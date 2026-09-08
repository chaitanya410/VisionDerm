# Camera-Based Skin Analysis — Design

**Date:** 2026-09-08
**Status:** Approved for planning
**Supersedes:** nothing (first spec in this repo)

## 1. Context

The app today accepts an uploaded photo and returns acne lesions found by a
hand-tuned classical CV heuristic (`backend/app/segmentation/classical.py`).
There is no trained model: `/api/health` reports
`unet_checkpoint_present: false`, and `backend/ml/` is scaffolding that has
never been run.

This spec takes the project to a live-camera skin analysis tool with real
trained models, self-care guidance, and a dermatologist finder.

**Purpose:** a mid-scale, publishable portfolio project demonstrating
end-to-end ML engineering. Optimised for *honest engineering that survives
scrutiny*, not for leaderboard accuracy.

**Hardware constraints (measured, not assumed):**

| Resource | Value | Consequence |
|---|---|---|
| GPU | GTX 1650, 4 GB VRAM | Fine for inference; marginal for training |
| System RAM | 3.8 GB visible, 1 × 4 GB stick | **Training locally is not viable** |
| Python | 3.14.7 | `torch` 2.14.0 resolves cleanly — verified |

All training happens in Kaggle Notebooks or Colab. Weights are published to
Hugging Face Hub. The local machine and the deployed demo run inference only.

## 2. Goals

1. Live camera preview that coaches the user toward a usable frame, then
   captures a still for real analysis.
2. Acne lesion detection with per-lesion boxes and a dermatologist-defined
   severity grade.
3. A 7-class skin condition screen that **abstains when uncertain** and
   escalates suspected malignancy to a clinician.
4. Self-care guidance keyed to acne severity, from citable sources.
5. Nearby dermatologist search, no API key, coarse location only.

## 3. Non-goals

- Diagnosis. This is an educational triage tool and says so everywhere.
- Continuous per-frame inference (rejected: flickers, degrades on blurry
  video, expensive on free hosting).
- Segmentation masks for acne — see §6.
- Treatment plans, prescriptions, or dosages.
- User accounts, history, or any image persistence.

## 4. Safety and medical framing

These are architectural constraints, not disclaimer text bolted on later.

**Abstention is a first-class output.** The classifier returns
`uncertain` when max calibrated probability falls below a tuned threshold.
The UI renders this as a real result ("Not confident enough to say — here's
how to get this looked at"), not an error.

**Malignancy routes hard.** If `melanoma`, `basal cell carcinoma`, or
`actinic keratosis` is the top class *or* appears above a low secondary
threshold, the response carries `escalate: true`. When `escalate` is set the
guidance module returns **no self-care content at all** — only clinician
referral and the dermatologist finder. This is enforced server-side in the
guidance module, not by frontend conditionals.

**The dangerous failure mode is the false negative.** Thresholds are tuned
for recall on malignant classes, accepting more false positives. This
tradeoff is stated in the README with the confusion matrix that justifies it.

**No "cure" language.** The word does not appear. Content is "self-care
measures that may help", sourced to the American Academy of Dermatology,
with links.

**Never persisted.** Images are processed in memory and discarded. No disk
writes, no logging of image bytes. Stated in the UI at capture time.

## 5. Architecture

```
Browser
  ├── CameraView ──── live MediaStream
  │     ├── FrameQualityGate   (client, ~5 fps, canvas only)
  │     │     └── face present? bright enough? sharp? big enough?
  │     └── PreviewOverlay     (client, cheap redness pass — labelled "preview")
  │
  └── capture() → single JPEG blob
        │
        ▼
FastAPI
  POST /api/analyze
    ├── decode + validate            (existing imaging.py)
    ├── AcneDetector    → boxes, count, Hayashi grade
    ├── ConditionScreen → 7-class probs, calibrated, may abstain
    ├── GuidanceEngine  → self-care content OR referral-only if escalate
    └── response (JSON, no overlay PNG — client draws)

  GET /api/clinics?lat&lon → OSM Overpass proxy, cached
```

The client draws boxes onto its own canvas over the captured still. The
server does **not** return a rendered overlay for the camera path: the
current `/api/segment` returns a ~978 KB base64 PNG per request (measured),
which is wasteful when the browser already holds the image.

`/api/segment` keeps its current behaviour for the existing upload flow.

## 6. Phase 2 — acne detection, not segmentation

**Finding that changed the design:** no usable public acne *segmentation*
dataset exists. [ACNE04](https://openaccess.thecvf.com/content_ICCV_2019/papers/Wu_Joint_Acne_Image_Grading_and_Counting_via_Label_Distribution_Learning_ICCV_2019_paper.pdf)
(Wu et al., ICCV 2019) — the standard benchmark, 1,457 images — provides
18,983 **bounding boxes** of a single lesion class, plus a dermatologist-
assigned Hayashi severity grade per image. Datasets with pixel masks
(ISIC 2018 Task 1) are dermoscopic melanoma images, irrelevant to acne.

So the model is a **detector**, and ACNE04 supplies both halves of the
product requirement: lesion locations *and* a clinical severity grade.

- **Model:** YOLOv8n fine-tuned on ACNE04. Small enough for CPU inference on
  free hosting.
- **Severity:** ACNE04 labels both a lesion count and a Hayashi grade per
  image. Grade is derived from the detector's predicted count using the
  Hayashi count thresholds, then validated against the dataset's own grade
  labels; if agreement is poor, fall back to a separate grading head. Either
  way this replaces the current invented heuristic with a clinical scale.
- **Known caveats to handle, not hide:**
  - ACNE04 is documented as containing low-quality images; a cleaning pass is
    part of the training notebook and its criteria are recorded.
  - Published cross-domain work shows ACNE04-trained models degrade on other
    sources. A webcam is another source. Measure the drop on a held-out set
    of webcam captures and publish it.

**Integration:** `LesionRegion` (`backend/app/segmentation/base.py:12`) is
already `bbox, area_px, centroid, score` — a detector fills this natively.
The new engine registers through `get_engine()` (`base.py:50`) alongside
`classical` and `unet`.

**Contract change:** `SegmentResponse.mask_png_base64` is currently required
(`schemas.py:39`). A detector has no mask. It becomes `str | None`, and
`area_px` becomes box area for detector results.

## 7. Phase 3 — condition screen

- **Data:** HAM10000, 7 classes (melanoma, melanocytic nevus, basal cell
  carcinoma, actinic keratosis, benign keratosis, dermatofibroma, vascular).
- **Model:** EfficientNet-B0, ImageNet-pretrained, fine-tuned.
- **Class imbalance:** HAM10000 is heavily skewed toward nevi. Use class-
  weighted loss; report per-class recall, never bare accuracy.
- **Calibration:** temperature scaling fitted on a validation split.
  Reliability diagram goes in the README — an uncalibrated softmax reported
  as "confidence" is the single most common flaw in projects of this type.
- **Abstention:** threshold tuned on validation to hit a target malignant-
  class recall.
- **Fairness:** HAM10000 skews toward lighter skin. Report performance
  stratified by estimated Fitzpatrick type and state the limitation plainly.

**Domain gap, stated honestly:** HAM10000 is dermoscopic; user input is a
webcam photo. Expect substantial degradation. The UI frames this feature as
"this looks worth showing a doctor", never as identification.

## 8. Phase 4 — guidance and clinic finder

**GuidanceEngine:** a pure function `(severity, escalate) → GuidanceCard[]`.
Static content, version-controlled as data (not code), each item carrying a
source URL. Returns referral-only content when `escalate` is true — enforced
here, server-side.

**Clinic finder:** OpenStreetMap Overpass API for
`healthcare=dermatologist` and nearby clinics; Nominatim for reverse
geocoding. Chosen over Google Places because it needs **no API key**, which
matters for a public repo, and no billing account.

- Location is requested only on explicit user action.
- Coordinates are rounded to ~1 km before leaving the browser.
- Responses cached server-side to respect Overpass rate limits.
- Overpass is unreliable under load: failures degrade to a "search on OSM"
  link rather than an error state.

## 9. Testing

| Layer | Approach |
|---|---|
| Engines | Synthetic fixtures as in existing `conftest.py`; detector contract tested with a stub checkpoint so tests run without weights |
| Guidance | Property test: `escalate=true` ⇒ zero self-care items. This is the safety invariant and gets its own test. |
| Calibration | Assert ECE below threshold on a fixed validation slice |
| API | Extend `test_api.py` for `/api/analyze` and `/api/clinics`, including abstention and escalation paths |
| Clinics | Mocked Overpass; explicit test for the degraded-failure path |
| Frontend | Component tests for the quality gate state machine |

Tests must pass with **no model weights present** — CI has no checkpoints.
Model-dependent tests skip cleanly, exactly as the current `unet` path does.

## 10. Deployment

- **Weights:** Hugging Face Hub, versioned, never in git.
- **Demo:** Hugging Face Spaces, free CPU tier.
- **Repo:** public. Datasets are never redistributed — only training
  notebooks and download scripts.
- **Licensing:** HAM10000 is CC BY-NC-SA 4.0; ACNE04 is research-use. Both
  are non-commercial. The repo carries a NOTICE recording dataset terms and
  the resulting restriction on derived weights.

## 11. Risks

| Risk | Mitigation |
|---|---|
| Webcam domain gap sinks real-world accuracy | Measure on self-collected webcam set; publish the number; frame feature as triage |
| ACNE04 label noise | Documented cleaning pass; ablation with and without |
| Free-tier cold starts (~30 s) | Warm-up ping; honest loading state |
| Scope sprawl across 4 phases | Each phase independently shippable and tagged; stop after any phase and still have a coherent project |
| Overpass rate limits | Cache; graceful degradation |

## 12. Open questions

1. Client-side face detection: MediaPipe Tasks Vision (small, WASM) vs a
   plain brightness/sharpness heuristic with no face model. Resolve in
   Phase 1 planning — MediaPipe is better UX but adds a ~2 MB WASM download
   that must be self-hosted for the Spaces deployment to stay dependency-free.
   The existing OpenCV Haar cascade already used by `classical.py` is a third
   option, but runs server-side and so cannot gate a live preview.
2. Whether `/api/analyze` supersedes `/api/segment` or runs alongside it
   permanently. Leaning alongside, deprecating `/api/segment` after Phase 2.
3. Self-collected webcam evaluation set: size and how it is labelled.

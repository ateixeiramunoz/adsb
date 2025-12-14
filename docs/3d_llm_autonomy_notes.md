# 3D-aware LLMs + autonomous waypoint navigation (technical notes)

These notes summarize the **technical feasibility** of combining:
- **3D-capable multimodal models** (for “seeing” 3D scenes, elevation, point clouds),
- **classical path planning** (for safe/optimal trajectories),
- **ArduPilot + MAVLink** (for executing missions and receiving waypoint/target updates),
- **local LLM runtimes** (for “mission compiler” UX: turning human intent into structured plans).

This document intentionally **does not** focus on a specific country/use-case/legislation.

---

## Key takeaway

**LLMs are great at intent → structured plan.**
For actual trajectories, use a **deterministic planner/optimizer** and treat the LLM as a **tool-calling “mission compiler”** that:
1) creates a planning spec (JSON),
2) calls a planner to compute the path + waypoints,
3) exports to ArduPilot-friendly mission formats,
4) validates constraints before upload.

---

## 1) “Can an LLM see in 3D?”

Yes, but it’s usually a **multimodal model** (3D/vision encoder + LLM), not a text-only model.

Common 3D inputs:
- **DEM / elevation rasters** (heightmaps, slope maps)
- **Point clouds** (LiDAR, photogrammetry reconstructions)
- **Meshes / scene graphs**

### Representative 3D-capable LMM projects (links)

- **LLaVA-3D** (ICCV 2025): 2D multi-view features + “3D patches” for spatially-aware reasoning  
  Repo: https://github.com/ZCMax/LLaVA-3D  
  Project page: https://zcmax.github.io/projects/LLaVA-3D/  

- **LSceneLLM** (CVPR 2025): large 3D scene understanding with adaptive preferences  
  Repo: https://github.com/Hoyyyaard/LSceneLLM  

- **3D-LLaVA** (CVPR 2025): point clouds + text for VQA / dense captioning / referring segmentation  
  Repo: https://github.com/djiajunustc/3D-LLaVA  
  Paper (CVF): https://openaccess.thecvf.com/content/CVPR2025/html/Deng_3D-LLaVA_Towards_Generalist_3D_LMMs_with_Omni_Superpoint_Transformer_CVPR_2025_paper.html  

- **PointLLM**: multimodal LLM for **colored point clouds** (object-level understanding)  
  Repo: https://github.com/InternRobotics/PointLLM  
  ECCV listing: https://eccv.ecva.net/virtual/2024/poster/879  

- Optional “related/nearby” projects you may run into:
  - **LLaVA-NeXT** (multi-image/video/3D task unification ideas): https://github.com/LLaVA-VL/LLaVA-NeXT  
  - **3DGraphLLM** (scene-graph + LLM for 3D VL tasks): https://github.com/CognitiveAISystems/3DGraphLLM  
  - **Video-3D LLM** (treats 3D scenes as dynamic video): https://github.com/LaVi-Lab/Video-3D-LLM  
  - Curated list (“awesome”): https://github.com/ActiveVisionLab/Awesome-LLM-3D  

---

## 2) Comparison: which 3D model type fits what you want?

| Option | “3D input” it expects | What it’s good at | What it’s *not* | Typical compute reality |
|---|---|---|---|---|
| LLaVA-3D | multi-view images + 3D correspondence (“3D patches”) | spatial reasoning + interaction tied to 2D views | not a turnkey path planner | usually needs a CUDA-capable GPU PC |
| LSceneLLM | large 3D scenes (research pipeline) | scene-level reasoning / preferences | not a plug-and-play drone nav stack | usually CUDA GPU PC |
| 3D-LLaVA | point clouds | 3D VQA, captioning, referring segmentation | not “mission planning” by itself | usually CUDA GPU PC |
| PointLLM | colored point clouds (often objects) | object-level understanding from points | full-scale mapping + nav | usually CUDA GPU PC |
| “LLM + 3D tools” (recommended) | **your own** structured 3D outputs (costmap, obstacles, DEM, etc.) | reliable navigation + waypoints + exports | doesn’t “see raw 3D” unless you add encoders | can run LLM locally + do geometry in code (CPU/GPU as needed) |

---

## 3) Hardware: what can realistically run what?

### 3.1 Running 3D multimodal models
Most 3D LMM research code assumes:
- **PyTorch**
- **NVIDIA GPU (CUDA)**

In practice:
- You’ll want a **desktop/laptop with an NVIDIA GPU** for interactive inference.
- “Training” or “serious finetuning” usually requires much more compute than inference.

### 3.2 Raspberry Pi + Coral: where it helps, where it doesn’t

A **Raspberry Pi** is great as a lightweight “companion computer” (networking, MAVLink routing, light perception).
It is *not* a good platform for running large 3D multimodal LLMs.

A **Coral Edge TPU** accelerates **TensorFlow Lite models compiled for the Edge TPU** (typically int8 pipelines).  
It does **not** run PyTorch 3D-LLMs or general LLM inference.  
Docs: https://www.coral.ai/docs/edgetpu/models-intro

**Practical takeaway:** Pi + Coral is good for “small vision model on-board” (detection/classification), not for “LLaVA-3D on-board”.

---

## 4) Software architecture that scales

### 4.1 Two-part split (recommended)
**(A) Planner/validator (deterministic code)**  
- Terrain + obstacles → safe route → waypoints  
- Constraint checks (geofence, max slope, min altitude, speed, turn limits)

**(B) LLM “mission compiler” (UX + structured output)**  
- Turns natural language into a strict JSON spec  
- Calls the planner + exporter tools  
- Explains results, but never “flies the drone”

### 4.2 Live vs offline autonomy
Both are feasible with ArduPilot/MAVLink:
- **Offline autonomy:** upload a full mission and let the flight controller execute it.
- **Live autonomy (when a link exists):** push mission updates or continuous setpoints.

---

## 5) ArduPilot + MAVLink: the practical interfaces

### 5.1 Companion computer pattern (on-drone)
ArduPilot docs:  
- Companion computers overview: https://ardupilot.org/dev/docs/companion-computers.html  
- Raspberry Pi via MAVLink (serial setup): https://ardupilot.org/dev/docs/raspberry-pi-via-mavlink.html  

### 5.2 Routing telemetry (drone ↔ ground station)
If you want to bridge MAVLink over serial + UDP/TCP:
- MAVLink Router (core project): https://github.com/mavlink-router/mavlink-router  
- ArduPilot MAVLink routing notes: https://ardupilot.org/dev/docs/mavlink-routing-in-ardupilot.html  

### 5.3 Missions and waypoints (chunk updates, robust)
- MAVLink Mission Protocol (upload/download missions): https://mavlink.io/en/services/mission.html  
- ArduPilot “planning a mission” overview: https://ardupilot.org/copter/docs/common-planning-a-mission-with-waypoints-and-events.html  

### 5.4 “Guided / offboard” control (continuous targets)
For sending live target setpoints:
- ArduPilot guided-mode commands: https://ardupilot.org/dev/docs/copter-commands-in-guided-mode.html  
- MAVLink offboard control interface summary: https://mavlink.io/en/services/offboard_control.html  
- MAVLink common message set: https://mavlink.io/en/messages/common.html  

---

## 6) Mission file formats you can generate/export

### 6.1 QGroundControl `.plan` (JSON)
- Official QGC plan file format: https://docs.qgroundcontrol.com/master/en/qgc-dev-guide/file_formats/plan.html  

### 6.2 MAVLink “defacto” plain-text mission files
- MAVLink file formats overview: https://mavlink.io/en/file_formats/  

---

## 7) Developer APIs / libraries (Python-friendly)

### MAVLink / Autopilot control
- **MAVSDK-Python** (high-level API, gRPC-based):  
  Repo: https://github.com/mavlink/MAVSDK-Python  
  Docs: https://mavsdk.mavlink.io/main/en/python/

- **pymavlink** (lower-level MAVLink access):  
  Repo: https://github.com/ArduPilot/pymavlink  

### Local LLM runtime + UI
- **Ollama** (run LLMs locally, simple API):  
  Repo: https://github.com/ollama/ollama  
  Site: https://ollama.com/  

- Optional UI for local models:
  - **Open WebUI** (often used with Ollama): https://github.com/open-webui/open-webui  

---

## 8) Planning / geometry building blocks (useful for “trajectory + waypoints”)

These are common, practical Python tools used in real projects:

### Geospatial + geometry
- **Shapely** (polygons, buffers, intersections): https://shapely.readthedocs.io/  
- **pyproj** (CRS + coordinate transforms): https://pyproj4.github.io/pyproj/  
- **Rasterio** (GeoTIFF/DEM rasters): https://rasterio.readthedocs.io/  
- **GDAL Python bindings** (low-level geodata access): https://gdal.org/en/stable/api/python/python_bindings.html  

### Graph routing + optimization
- **NetworkX** (graphs, shortest paths): https://networkx.org/  
- **OR-Tools** (routing/TSP/VRP):  
  Repo: https://github.com/google/or-tools  
  Python reference: https://developers.google.com/optimization/reference/python/index_python  

### Path primitives / smoothing
- **Dubins paths** (turn-radius constrained paths): https://github.com/AndrewWalker/pydubins  
- **SciPy optimize** (smoothing, constrained optimization): https://docs.scipy.org/doc/scipy/reference/optimize.html  

---

## 9) “Live processing on ground station, drone executes” — what actually happens

A robust implementation typically looks like this:

1. **Sensor/state ingestion**
   - Drone autopilot publishes telemetry over MAVLink.
   - Optional companion computer routes MAVLink to the ground station (UDP/TCP).

2. **World model**
   - Ground station fuses: map data (DEM/obstacles) + live telemetry (+ optional vision inference).
   - If you add a 3D LMM, it should output structured facts (“obstacle here”, “landing zone there”), not raw control.

3. **Planning**
   - Deterministic code computes route + waypoints.
   - Validation step ensures constraints are met.

4. **Commanding**
   - Upload a mission (Mission Protocol), or
   - Send guided/offboard setpoints (continuous) if you truly need real-time target updates.

5. **Safety**
   - The flight controller always enforces low-level stability/failsafes.
   - If the link drops, the drone continues mission or executes configured failsafe behavior.

---

## 10) Suggested “first build” milestones (no research-repo pain)

1) **SITL simulation first**  
   - ArduPilot SITL overview: https://ardupilot.org/dev/docs/sitl-simulator-software-in-the-loop.html  

2) **Generate a QGC `.plan` mission from Python**  
   - Use your planner → export `.plan` JSON.

3) **Upload mission via MAVSDK or pymavlink**  
   - Start with simple waypoint missions, then add constraints and replanning.

4) **Add an LLM only as a spec compiler**  
   - Small local model via Ollama generates JSON specs.
   - Your code validates + executes.

5) **Only then add 3D multimodal models** (if you truly need “3D perception” rather than “map-based planning”).

---

## 11) Notes on “training” an LLM for this

A pragmatic approach:
- Don’t train it to “discover optimal trajectories”.
- Train/fine-tune it to:
  - produce **your** JSON schema correctly,
  - call the right tools,
  - explain/diagnose failures from validator reports.

Training data can be synthetic:
- Random scenarios → planner produces labels → LLM learns to emit the correct spec.

---

### End
If you want, you can paste this file into your repo as a starting “design notes” doc and iterate from there.

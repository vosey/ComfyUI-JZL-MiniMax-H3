MiniMax H3 Semantic Bridge v1.0 — Exact Release Build
=========================================================

This release is built directly from the previously tested working
Distilled node. The numerical inference path has not been rewritten.

Only release-facing items were changed:
- public node display names
- public model folder name
- UI category
- console/cache messages
- documentation paths

The adapter math, model loading precision, normalization, magnitude matching,
blend equation, H3 tokenization, keyframe handling, and latent creation are
the same as in the tested working build.

INSTALLATION
------------

1. Copy this folder:

   MiniMax_H3_Semantic_Bridge

   to:

   ComfyUI/custom_nodes/

2. Create:

   ComfyUI/models/semantic_bridge/

3. Copy the adapter there:

   MiniMaxH3_SemanticBridge_v1.safetensors

Final structure:

ComfyUI/
├─ custom_nodes/
│  └─ MiniMax_H3_Semantic_Bridge/
│     ├─ __init__.py
│     ├─ nodes.py
│     ├─ README.txt
│     └─ ADAPTER_INSTALLATION.txt
└─ models/
   └─ semantic_bridge/
      └─ MiniMaxH3_SemanticBridge_v1.safetensors

4. Restart ComfyUI.

NODES
-----

MiniMax H3 Image to Video + Semantic Bridge
MiniMax H3 Semantic Bridge
MiniMax H3 Clear Semantic Bridge Cache

RECOMMENDED SETTINGS
--------------------

alpha = 0.10
magnitude_match = per_token

IMPORTANT
---------

The public standalone release does not require SenseNova at inference time.

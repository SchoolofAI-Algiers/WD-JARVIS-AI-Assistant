---
title: SOAI Algiers Featured Projects
source: School of AI Algiers
category: projects
lang: en
---

# SOAI Algiers Featured Projects

## 1. Language-Guided Robotic Manipulation

Repository: https://github.com/SchoolofAI-Algiers/language-guided-robotics

### Description

Language-Guided Robotic Manipulation is a multimodal deep reinforcement learning system that enables a simulated robotic arm to understand natural-language instructions and interact with objects.

The project combines:
- Language embeddings
- Visual perception
- Spatial information
- PPO-based visuomotor control

The system uses a 7-DOF KUKA IIWA robot simulated in PyBullet.

Several architectures were evaluated, including:
- A standard ResNet18 baseline
- SigLIP
- A spatial-fusion ResNet18 combining RGB information with an instance segmentation mask

## 2. Physics-Aware Transformer

Repository: https://github.com/SchoolofAI-Algiers/physics-aware-transformer

### Description

Physics-Aware Transformer is a research framework that combines Fourier Neural Operators with Transformer-based physics-informed learning to solve partial differential equations.

The proposed FNO-Transformer architecture is evaluated against PINN and PINNsFormer baselines on several problems, including:
- Reaction
- Convection
- Wave equations
- Burgers equation
- 2D Navier-Stokes equations

The project combines:
- Spectral methods
- Spatio-temporal modeling
- Physics-informed learning
- Reproducible numerical experiments

## 3. Safe Multi-Agent Reinforcement Learning for UAVs

Repository: https://github.com/SchoolofAI-Algiers/UAVs-SAFE-MARL

### Description

Safe Multi-Agent Reinforcement Learning for UAVs is a research framework for learning autonomous UAV behaviors while enforcing explicit safety constraints.

The project combines multi-agent reinforcement learning with safety mechanisms including:
- Safety wrappers
- Control Barrier Functions
- Model Predictive Safety Control

Experiments cover:
- Multi-agent quadrotor hovering
- Fixed-wing dogfighting
- Benchmark control environments

The goal is to make learned policies safer and more reliable during execution.
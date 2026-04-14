# SplatNav: Autonomous 3D Mapping with ROS 2 and Python

> **It is a robot that can be dropped into a completely unknown environment and autonomously drive itself around until it has built a mathematically perfect, photorealistic 3D replica of that environment, without a human ever touching a joystick.**

---

## What This Project Does

This project makes a Clearpath Jackal robot explore and map unknown areas entirely on its own. Instead of just driving around randomly to avoid walls, the robot actively looks at its own map, finds the blurry or incomplete areas, and drives there to get a better look.

It combines five main pieces:
- **ROS 2 Jazzy & Gazebo:** The core software and simulation environment for the robot.
- **PINGS:** A mapping tool that uses camera and LiDAR data to build two things at once: a highly detailed 3D visual map, and a flat 2D collision map so the robot doesn't crash.
- **GauSS-MI:** The exploration "brain." It stays on the original ROS 1 Noetic stack from the author.
- **Relay layer:** A small socket-based relay that forwards camera, depth, pose, and next-best-view data between ROS 2 and ROS 1.
- **Python (`rclpy`):** The main control program. It grabs the coordinates from the brain and sends them to the robot's driving system.

---

## How We Handle Software Conflicts

The mapping algorithms (PINGS and GauSS-MI) were built by researchers using older software (ROS 1 and CUDA 11.8). Our robot uses the newest software (ROS 2 Jazzy and Ubuntu 24.04).

To prevent everything from breaking, we use a split Docker setup. The main robot stack runs inside a modern ROS 2 Docker container. GauSS-MI stays in its original ROS 1 Noetic container, and a small relay process forwards data between the two stacks over a local socket.

---

## System Architecture

```text
Gazebo Simulation (Jackal)
       │
       ├─► Camera + LiDAR Data ────────────┐
       │                                   │
       ▼                                   ▼
[ ROS 2 Jazzy Stack ]               [ GauSS-MI ROS 1 Container ]
PINGS, Python control, Nav2         Original ROS 1 exploration brain
       │                                   │
       ├─► Relay to ROS 1                ├─► Next Target Coordinate
       │                                   │
       ▼                                   ▼
[ Socket Relay ]                   [ ROS 1 GauSS-MI Topics ]
Forwards image/pose/NBV           /camera/bgr, /camera/depth, /camera/pose
       │                                   │
       └──────────────► [ Nav2 / Controller ] ◄─────────┘
                           │
                           ▼
                 Drive Commands to Robot
```

---

## Repository Structure

```text
splat-nav/
│
├── docker/                # Setup files for the container and Conda
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── gaussmi/               # Original GauSS-MI ROS 1 source tree
│
├── relay/                 # Shared socket relay code between ROS 2 and ROS 1
│
├── ros2_ws/               # Main workspace
│   └── src/
│       ├── spin_robot_node/ # Simple Python controller
│       ├── gaussmi_relay/   # ROS 2 relay code
│       └── launch/          # Startup scripts
│
├── logs/                  # Saved maps and test results
└── README.md
```

---

## System Requirements

- Ubuntu 22.04 or 24.04 (Host computer)
- Docker + Docker Compose
- NVIDIA GPU
- `nvidia-container-toolkit` installed on host

---

## Setup Instructions

### 0. Clone submodules
After cloning the repository, initialize and fetch submodules:

```bash
git submodule update --init --recursive
```

This fetches the original GauSS-MI ROS 1 code into gaussmi/.

### 1. Prepare the VM (required on every brand-new barebones VM)
Any time you create a new barebones VM, run this first before anything else.
On the same VM, you generally only do this one time.

From repo root:
```bash
cd /home/shooty/ros2-nerf-jackal
chmod +x setupvm.bash
./setupvm.bash
newgrp docker
```

`setupvm.bash` installs Docker, NVIDIA Container Toolkit, and configures Docker runtime via `nvidia-ctk`.

Then finish VNC setup:
```bash
vncpasswd
systemctl --user daemon-reload
systemctl --user start vncserver@1
```

When done for the day:
```bash
systemctl --user stop vncserver@1
```

If you reboot later, you do not need to rerun `setupvm.bash`.

### 2. Build the Docker Container
```bash
cd docker
docker compose build
```

To start the core stack with ROS 2 and the relay:

```bash
cd ros2_ws
just compose-up-gaussmi
```

To include the optional ROS 1 GauSS-MI sidecar:

```bash
cd ros2_ws
just compose-up-gaussmi-ros1
```

To stop it:

```bash
just compose-down-gaussmi
```

### 3. Option A (VNC): SSH from your laptop and open the render tunnel
```bash
ssh -L 5901:localhost:5901 <user>@<vm-ip>
```

Open your VNC client and connect to:
```text
localhost:5901
```

### 4. Start container with GUI forwarding on VNC display
```bash
cd /home/shooty/ros2-nerf-jackal/docker
export DISPLAY=:1
./setup-x11.sh
docker compose up -d
docker exec -it ros2_jackal_nerf bash
```

`./setup-x11.sh` handles X11 permissions (`xhost +local:docker`) and prepares `/tmp/.docker.xauth`.

### 5. Option B (No VNC): SSH X11 forwarding directly to your laptop
From your laptop:
```bash
ssh -Y <user>@<vm-ip>
```

On the VM (inside that same SSH session):
```bash
echo "$DISPLAY"            # expected: localhost:10.0 (or similar)
cd /home/shooty/ros2-nerf-jackal/docker
./setup-x11.sh
docker compose up -d
docker exec -it ros2_jackal_nerf bash
```

Inside the container, test GUI first:
```bash
xeyes
```

Then launch simulation with the preconfigured env:
```bash
cd /workspace
just launch-sim
```

To run the GauSS-MI sidecar stack alongside the ROS 2 system:
```bash
cd /workspace
just compose-up-gaussmi
```

The compose stack starts the core services:
- ros2: ROS 2 Jazzy robot and simulation stack
- gaussmi_relay: ROS 2 relay node that forwards data over a socket

The optional ROS 1 sidecar is only started with the gaussmi profile:
- gaussmi_ros1: the original ROS 1 GauSS-MI container

The relay forwards:
- ROS 2 to ROS 1: /camera/bgr, /camera/depth, /camera/pose
- ROS 1 to ROS 2: /gaussmi/nbv_pose

Notes:
- `docker-compose.yml` uses `network_mode: host`, which is required for SSH X11 forwarding because `localhost:10.0` must resolve to the host SSH tunnel, not container loopback.
- `setup-x11.sh` supports both local/VNC displays (`:0`, `:1`) and SSH-forwarded displays (`localhost:10.0`).
- `just launch-sim` sets `XDG_RUNTIME_DIR`, `GZ_PARTITION`, `IGN_PARTITION`, `GZ_IP`, and `IGN_IP` so Gazebo server/client and `ros_gz_sim` discover each other reliably.

Inside the container, set up the isolated math environment for PINGS if needed:
```bash
conda env create -f /workspace/src/pings_ros2/environment.yml
```

---

## Building the Code

Inside the container:
```bash
source /opt/ros/jazzy/setup.bash
cd /workspace
colcon build --symlink-install
```

To build and run the Python controller:
```bash
source /opt/ros/jazzy/setup.bash
cd /workspace
colcon build --packages-select spin_robot_node --symlink-install
source /workspace/install/setup.bash
ros2 run spin_robot_node spin_robot_node
```

---

## Project Phases

**Phase 1 — Basic Setup:** Get the Jackal driving in Gazebo and ensure the Docker container can use the GPU.  
**Phase 2 — GauSS-MI Sidecar:** Keep GauSS-MI on ROS 1 and connect it to the ROS 2 stack with a relay.  
**Phase 3 — Live Mapping:** Connect the PINGS mapper so it updates in real-time as the robot drives, rather than using pre-recorded data.  
**Phase 4 — Python Control:** Keep the controller simple and readable with `rclpy`.  
**Phase 5 — Full Autonomy:** Drop the robot into a simulated building and let it map the whole thing by itself.  

---

## Evaluation

To prove this system works better than standard mapping, we will measure:
- **Map Quality:** How clear and realistic the final 3D map looks.
- **Speed:** How fast the robot can fully map the room.
- **Safety:** Making sure the robot never crashes into walls while exploring.

---

## License
MIT


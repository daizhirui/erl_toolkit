#!/usr/bin/env python3
#run_docker
import argparse
import os
import socket
import sys

def build_docker_run_cmd(image: str) -> str:
    script_dir = os.path.dirname(os.path.realpath(__file__))
    home_dir   = os.path.abspath(os.path.join(script_dir, os.pardir))

    xauth    = os.path.join(home_dir, ".Xauthority")
    if not os.path.isdir(home_dir):
        print(f"[ERROR] Could not find home directory '{home_dir}'.", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(xauth):
        print(f"[WARNING] XAUTHORITY file '{xauth}' does not exist. Continuing anyway...", file=sys.stderr)

    display    = os.environ.get("DISPLAY", "")
    ros_master = os.environ.get("ROS_MASTER_URI", "http://localhost:11311")
    ros_host   = os.environ.get("ROS_HOSTNAME", "localhost")

    ros_cache = os.path.join(home_dir, ".ros")
    os.makedirs(ros_cache, exist_ok=True)

    cmd_parts = [
        "docker run -it",
        "--network host",
        f"-e HOME={home_dir}",
        f"-e ROS_HOME={ros_cache}",
        f"-e DISPLAY={display}",
        f"-e XAUTHORITY={xauth}",
        f"-e ROS_MASTER_URI={ros_master}",
        f"-e ROS_HOSTNAME={ros_host}",
        f"-v {home_dir}:{home_dir}",
        f"-v /etc/passwd:/etc/passwd:ro",
        f"-v /etc/group:/etc/group:ro",
        f"-v {xauth}:{xauth}:ro",
        f"-v {ros_cache}:{ros_cache}",
        "-v /tmp/.X11-unix:/tmp/.X11-unix:ro",
        image 
    ]
    return " \\\n  ".join(cmd_parts)

def main():
    parser = argparse.ArgumentParser(
        description="Run a docker"
    )
    parser.add_argument(
        "--image",
        "-i",
        type=str,
        required=True,
        help="Docker image."
    )
    args = parser.parse_args()
    run_cmd = build_docker_run_cmd(args.image)
    print(f"[INFO] Running:\n\n{run_cmd}\n")
    os.system(run_cmd)

if __name__ == "__main__":
    main()

import argparse
import os.path
import sys
import socket
import time
from typing import List

import docker
import docker.errors

from erl_toolkit.docker import CONFIG_DIR
from erl_toolkit.docker.common import get_container
from erl_toolkit.log import get_logger


def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    addr = s.getsockname()[0]
    s.close()
    return addr


logger = get_logger(__name__)


def create_container(
    name: str,
    image: str,
    command: str = None,
    entrypoint: str = None,
    enable_x11: bool = True,
    auto_remove: bool = False,
    dns: List[str] = None,
    environment: dict = None,
    env_vars: List[str] = None,
    gpu: bool = False,
    dev: bool = False,
    gui: bool = False,
    group_add: list = None,
    ports: list = None,
    mounts: list = None,
    privileged: bool = True,
    restart_policy: dict = None,
    tty: bool = True,
    volumes: list = None,
    user: str = None,
    sshd: bool = False,
):
    if "ERL_IN_CONTAINER" in os.environ:
        logger.warning(f"You are in the container {os.environ['ERL_IN_CONTAINER']}")
        return
    client = docker.from_env()
    container = get_container(name)
    if container is not None:
        logger.warning(f"The container {name} already exist.")
        p = input("Do you want to remove the container? [y/N]")
        if len(p) == 0:
            p = "n"
        if p.lower() == "y":
            try:
                if container.status != "exited":
                    logger.warning(f"The container status is {container.status}.")
                    p = input("Do you want to stop it? [y/N]")
                    if p.lower() == "y":
                        container.stop()
                    else:
                        exit(0)
                container.remove()
            except docker.errors.APIError as e:
                print(e)
                exit(1)
        elif p.lower() == "n":
            return

    if command is None:
        command = "bash -l"

    # skip dns setting to make it work when host network is changed
    # if dns is None:
    #     with open("/etc/resolv.conf", "r") as file:
    #         dns = file.readlines()
    #     dns = [x.split(" ")[1].strip() for x in dns if x.startswith("nameserver")]
    #     dns = [x for x in dns if x[0].isnumeric() and x != "127.0.0.1"]

    if environment is None:
        environment = dict()
    environment["ERL_IN_CONTAINER"] = name
    environment["ERL_DOCKER_IMAGE"] = image
    environment["TZ"] = "America/Los_Angeles"
    environment["DOCKER_HOST"] = get_ip_address()

    if restart_policy is None:
        restart_policy = dict(Name="always")

    if volumes is None:
        volumes = set()
    else:
        volumes = set(volumes)
    if gui:
        enable_x11 = True
    if enable_x11:
        if not os.path.exists("/tmp/.X11-unix"):
            logger.warning("X11 is unavailable: /tmp/.X11-unix does not exist.")
            exit(1)
        volumes.add("/tmp/.X11-unix:/tmp/.X11-unix")
    for volume in [
        "/var/run/docker.sock",
        "/dev/bus",
        "/dev/block",
        "/dev/char",
        "/dev/serial",
        "/dev/shm",
    ]:
        volume_str = f"{volume}:{volume}:rw"
        if dev and volume.startswith("/dev"):
            continue  # skip /dev/* because /dev will be mounted
        if volume_str not in volumes:
            volumes.add(volume_str)
    if dev:
        volumes.add("/dev:/dev")
    for volume_str in [f"{CONFIG_DIR}:/mnt/docker_login:ro", f"{os.environ['HOME']}:/home/{user}:rw"]:
        if volume_str not in volumes:
            volumes.add(volume_str)
    volumes = list(volumes)

    # c = client.containers.run(
    #     image=image,
    #     command=command,
    #     auto_remove=auto_remove,
    #     detach=True,
    #     dns=dns,
    #     entrypoint=entrypoint,
    #     environment=environment,
    #     group_add=group_add,
    #     hostname=f"{socket.gethostname()}-container-{name}",
    #     mounts=mounts,
    #     name=name,
    #     privileged=privileged,
    #     restart_policy=restart_policy,
    #     tty=tty,
    #     user=None,
    #     volumes=volumes,
    #     working_dir=f"/home/{user}",
    # )
    cmd = "docker run "
    if auto_remove:
        cmd = cmd + "--rm "
    if dns is not None:
        for d in dns:
            cmd = cmd + f"--dns {d} "
    if environment is not None:
        for k, v in environment.items():
            cmd = cmd + f"-e {k}={v} "
    if env_vars is not None:
        for env_var in env_vars:
            cmd += f"-e {env_var} "
    if group_add is not None:
        for g in group_add:
            cmd = cmd + f"--group-add {g} "
    if ports is not None:
        for port in ports:
            cmd = cmd + f"-p 127.0.0.1:{port} "
    if mounts is not None:
        for m in mounts:
            cmd = cmd + f"-v {m} "
    if privileged:
        cmd = cmd + "--privileged "
    if restart_policy is not None:
        cmd = cmd + f"--restart {restart_policy['Name']} "
    if tty:
        cmd = cmd + "-t "
    if volumes is not None:
        for v in volumes:
            cmd = cmd + f"-v {v} "
    cmd = cmd + f"--workdir /home/{user} "
    if gpu:
        cmd = cmd + "--gpus all "
    if entrypoint is not None:
        cmd = cmd + f"--entrypoint {entrypoint} "
    if gui:
        os.system("xhost +SI:localuser:root")
        cmd = cmd + "-e DISPLAY "
        cmd = cmd + f"-v {os.environ['HOME']}/.Xauthority:/root/.Xauthority:rw "
    cmd = cmd + f"--net=host "
    cmd = cmd + "--detach "
    cmd = cmd + f"--hostname container-{name} --add-host=container-{name}:127.0.0.1 "
    cmd = cmd + f"--name {name} "
    cmd = cmd + "--cap-add sys_ptrace "  # required to debug program in container
    cmd = cmd + "--cpus=0 --memory-swap=-1 "  # gives no limits of CPU and memory-swap
    cmd = cmd + "--ipc=host "  # use the host's Inter-Process-Communication namespace
    cmd = cmd + f"{image} "
    cmd = cmd + command
    logger.info(f"Container {name} is created: {cmd}")
    os.system(cmd)

    c = client.containers.get(name)
    t0 = time.time()
    while time.time() - t0 < 5:
        if c.status == "running":
            break
        time.sleep(0.1)

    if sshd:
        logger.info(f"Starting SSHD in container {name}...")
        c.exec_run(user="root", tty=True, cmd=f"/usr/sbin/sshd")

    if sys.platform == "linux" and user is not None:
        if user != "root":
            # different linux distributions have different user information
            # so we need to copy only the specified user information from host to container
            logger.info(f"Copying user information from host to container {name}...")
            for f in ["passwd", "group", "shadow"]:
                src_file = os.path.join("/etc", f)
                dst_file = os.path.join(CONFIG_DIR, f)
                if not os.path.exists(src_file):
                    logger.warning(f"{src_file} does not exist.")
                    continue
                os.system(f"sudo grep {user} {src_file} > {dst_file}")
                c.exec_run(user="root", tty=True, cmd=f"bash -c 'cat {dst_file} >> {src_file}'")
                os.system(f"sudo rm {os.path.join(CONFIG_DIR, f)}")
            logger.info(f"Add user {user} to sudo group...")
            c.exec_run(user="root", tty=True, cmd=f"bash -c 'usermod -aG sudo {user}'")
            if gui:
                logger.info(f"Creating /run/user/$(id -u {user}) in container {name}...")
                c.exec_run(user="root", tty=True, cmd=f"bash -c 'mkdir -p /run/user/$(id -u {user})'")
                c.exec_run(user="root", tty=True, cmd=f"bash -c 'chown {user}:{user} /run/user/$(id -u {user})'")
                logger.info(f"Setting XDG_RUNTIME_DIR in container {name}...")
                c.exec_run(
                    user="root",
                    tty=True,
                    cmd="bash -c \"echo 'export XDG_RUNTIME_DIR=/run/user/$(id -u $USER)' >> /etc/profile\"",
                )
    else:
        print(f"YOU MAY NEED TO LOGIN AS ROOT TO CREATE USER {user} at first:")
        print(f"erl-login-container --name {name} --user root")
        print(f"adduser {user}")
        print(f"usermod -aG sudo {user}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", type=str, required=True, metavar="CONTAINER_NAME")
    parser.add_argument("--image", type=str, required=True)
    parser.add_argument("--gpu", action="store_true", help="Connect all GPUs to the container")
    parser.add_argument("--dev", action="store_true", help="Connect all devices to the container")
    parser.add_argument("--gui", action="store_true", help="Connect DISPLAY to the container")
    parser.add_argument("--command", type=str)
    parser.add_argument("--overwrite-entrypoint", action="store_true")
    parser.add_argument("--auto-remove", action="store_true", help="Automatically remove the container when it exits")
    parser.add_argument("--mounts", type=str, action="append", help="Mount host directory to container")
    parser.add_argument("--ports", type=str, nargs="+", help="Ports to map from the container to the host")
    parser.add_argument("--user", type=str, default=f"{os.environ['USER']}", help=f"Default: {os.environ['USER']}")
    parser.add_argument("--sshd", action="store_true", help="Enable SSHD")
    parser.add_argument(
        "--env",
        type=str,
        nargs="+",
        help="Environment variables to set in the container (e.g., --env VAR1 VAR2=value2)",
    )
    parser.add_argument(
        "--extra-args",
        type=str,
        help="Extra arguments for the docker exec command",
    )

    args = parser.parse_args()
    entrypoint = None
    if args.overwrite_entrypoint:
        entrypoint = args.command
    if args.mounts is not None:
        mounts = []
        for mount in args.mounts:
            if ":" in mount:
                mount = mount.split(":")
                mount[0] = os.path.abspath(mount[0])
                mount = ":".join(mount)
            else:
                mount = os.path.abspath(mount)
                mount = f"{mount}:{mount}"
            mounts.append(mount)
        args.mounts = mounts
    create_container(
        name=args.name,
        image=args.image,
        command=args.command,
        entrypoint=entrypoint,
        auto_remove=args.auto_remove,
        env_vars=args.env,
        gpu=args.gpu,
        gui=args.gui,
        ports=args.ports,
        mounts=args.mounts,
        dev=args.dev,
        user=args.user,
        sshd=args.sshd,
    )


if __name__ == "__main__":
    main()

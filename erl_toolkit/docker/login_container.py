import argparse
import os

import docker

from erl_toolkit.docker import CONTAINER_SHELL
from erl_toolkit.docker.common import get_container
from erl_toolkit.log import get_logger

logger = get_logger(__name__)


def login_container(name: str, user: str, shell: str, env_vars: list = None, extra_args: str = None):
    container = get_container(name)
    if container is None:
        logger.warning(f"No container named {name}. " "Please create it by erl-docker-create-container at first.")
        exit(1)

    if user == "root":
        home = "/root"
    else:
        home = f"/home/{user}"

    cmd = f"xhost +si:localuser:{user}"
    print(cmd)
    os.system(cmd)
    cmd = (
        f"docker exec --privileged --interactive --tty --env SHELL={shell} "
        f"--env TERM={os.environ['TERM']} --env USER={user} "
        f"--env=DISPLAY --env=QT_X11_NO_MITSHM=1 "
        f"--user {user} "
        f"--env HOME={home} "
    )
    if env_vars is not None:
        for env_var in env_vars:
            cmd += f"--env {env_var} "
    if extra_args is not None:
        cmd += f"{extra_args} "
    cmd += f"{name} {shell} -l"
    print(cmd)
    os.system(cmd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", type=str, required=True, metavar="CONTAINER_NAME")
    parser.add_argument("--user", type=str, default=os.environ["USER"])
    parser.add_argument(
        "--shell",
        type=str,
        default=CONTAINER_SHELL,
        help=f"Default: {CONTAINER_SHELL}",
    )
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
    login_container(args.name, args.user, args.shell, args.env, args.extra_args)


if __name__ == "__main__":
    main()

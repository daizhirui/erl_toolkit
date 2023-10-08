import os
import sys

sys.path.append(os.path.dirname(__file__))

from erl_toolkit.archlinux.ros_noetic.dependencies import dependencies
from erl_toolkit.archlinux.ros_noetic.sink_packages import sink_packages
from tqdm import tqdm
from argparse import ArgumentParser

if "/opt/intel/oneapi/mkl/latest/lib/intel64" not in os.environ.get("LD_LIBRARY_PATH", ""):
    os.environ["LD_LIBRARY_PATH"] = "/opt/intel/oneapi/mkl/latest/lib/intel64:" + os.environ.get(
        "LD_LIBRARY_PATH", ""
    )  # to make numpy-mkl work

sink_packages = list(set(sink_packages))
sink_packages.sort()

alternative_selections = {
    "pkg-config": "pkgconf",
    "opencv": "opencv-cuda",
    "python-sip4": "sip4",
    "sip": "python-sip",
    "python-pyqt5": "python-pyqt5-sip4",
    "python-numpy": "python-numpy-mkl",
}

use_git_packages = [
    "eigen",
    "gazebo",
    "pcl",
    "fcl",
]

aur_package_urls = {
    "sip4": "https://github.com/daizhirui/sip4.git",
    "pcl-git": "https://github.com/daizhirui/pcl-git.git",
    "libdart": "https://github.com/daizhirui/AUR-libdart.git",
    "gazebo-git": "https://github.com/daizhirui/aur-gazebo-git.git",
    "ros-noetic-qt-gui-cpp": "https://github.com/daizhirui/ros-noetic-qt-gui-cpp.git",
    "ros-noetic-pybind11-catkin": "https://github.com/daizhirui/ros-noetic-pybind11-catkin.git",
    "ros-noetic-robot-state-publisher": "https://github.com/daizhirui/ros-noetic-robot-state-publisher.git",
    "ros-noetic-rosbag": "https://github.com/daizhirui/ros-noetic-rosbag.git",
    "ros-noetic-depth-image-proc": "https://github.com/daizhirui/ros-noetic-depth-image-proc.git",
    "ros-noetic-laser-assembler": "https://github.com/daizhirui/ros-noetic-laser-assembler.git",
    "ros-noetic-laser-filters": "https://github.com/daizhirui/ros-noetic-laser-filters.git",
}

parser = ArgumentParser(description="Install/fix ros-noetic-desktop-full and its dependencies.")
parser.add_argument(
    "--start-from",
    nargs="+",
    default=[],
    metavar="PACKAGES",
    help="Start the installation from these packages, and install other packages requiring them.",
)
args = parser.parse_args()
args_start_from = set(args.start_from)

# compute the order of installation
dependency_graph = {k: set(v) for k, v in dependencies.items()}

if len(args_start_from) > 0:
    # compute the reverse dependency graph
    rdependency_graph = dict()
    for package_name, package_dependencies in dependencies.items():
        for dependency in package_dependencies:
            if dependency not in rdependency_graph:
                rdependency_graph[dependency] = set()
            rdependency_graph[dependency].add(package_name)

    sink_packages = list(set(args.start_from))

    tiny_dependency_graph = dict()
    involved_packages = set(sink_packages)
    while len(involved_packages) > 0:
        next_involved_packages = set()
        for package in involved_packages:
            if package not in rdependency_graph:  # top-level package
                continue
            for affected_pkg in rdependency_graph[package]:  # affected packages
                if affected_pkg not in tiny_dependency_graph:
                    tiny_dependency_graph[affected_pkg] = set()
                    next_involved_packages.add(affected_pkg)
                tiny_dependency_graph[affected_pkg].add(package)
        involved_packages = next_involved_packages

    order = [sink_packages]
    while len(tiny_dependency_graph) > 0:
        cur_order = order[-1]
        next_order = set()
        for package in cur_order:
            for required_by in tiny_dependency_graph.keys():
                tiny_dependency_graph[required_by].discard(package)  # remove the dependency
                if len(tiny_dependency_graph[required_by]) == 0:  # no more dependencies, can be installed
                    next_order.add(required_by)
        for package in next_order:
            del tiny_dependency_graph[package]
        if len(next_order) == 0:
            if len(tiny_dependency_graph) > 0:
                print("Circular/Incomplete dependency detected!")
                sys.exit(1)
        order.append(list(next_order))
else:
    order = [sink_packages]
    while len(dependency_graph) > 0:
        cur_order = order[-1]
        next_order = set()
        for package in cur_order:
            for required_by in dependency_graph.keys():
                dependency_graph[required_by].discard(package)  # remove the dependency
                if len(dependency_graph[required_by]) == 0:  # no more dependencies, can be installed
                    next_order.add(required_by)
        for package in next_order:
            del dependency_graph[package]
        if len(next_order) == 0:
            if len(dependency_graph) > 0:
                print(dependency_graph)
                print("Circular/Incomplete dependency detected!")
                sys.exit(1)
            break
        order.append(list(next_order))

answer = input("Do you want to start installing? [y/N] ")
if answer.lower() != "y":
    sys.exit(0)


def exit_on_failure(cmd):
    if os.system(cmd) != 0:
        sys.exit(1)


# install packages
paru_dir = os.path.join(os.environ["HOME"], ".cache", "paru", "clone")
os.chdir(paru_dir)
installed_packages = set()
if os.path.exists("progress.txt"):
    with open("progress.txt", "r") as f:
        installed_packages = set([line.strip() for line in f.readlines()])
with open("progress.txt", "a+") as progress:
    pbar = tqdm(total=sum([len(packages) for packages in order]), ncols=80)
    for packages in order:
        for package in packages:
            if package in alternative_selections:
                package = alternative_selections[package]
            if package in use_git_packages:
                package = f"{package}-git"
            if package in installed_packages:
                pbar.update()
                continue
            if not os.path.exists(package):
                if package in aur_package_urls:
                    os.system(f"git clone {aur_package_urls[package]} {package}")
                else:
                    if os.system(f"paru -G {package}") != 0:
                        os.system(f"paru -S {package} --noconfirm")
                        installed_packages.add(package)
                        progress.write(f"{package}\n")
                        progress.flush()
                        pbar.update()
                        continue
            os.chdir(package)
            if package in aur_package_urls:
                os.system(f"git remote set-url origin {aur_package_urls[package]}")
            os.system("git pull")  # update the package
            if os.system("makepkg -si --noconfirm -c") != 0:
                exit_on_failure(f"paru -S {package} --noconfirm")
            exit_on_failure("rm -rf pkg src *.pkg.tar.zst")
            os.chdir(paru_dir)
            installed_packages.add(package)
            progress.write(f"{package}\n")
            progress.flush()
            pbar.update()
os.remove("progress.txt")
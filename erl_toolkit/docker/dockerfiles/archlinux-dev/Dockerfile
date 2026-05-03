FROM archlinux/archlinux:base-devel

RUN pacman -Syyu && pacman -S --noconfirm zsh \
    inetutils git vim cargo python-pip openssh

    RUN sed -i 's/# %wheel ALL=(ALL:ALL) ALL/%wheel ALL=(ALL:ALL) ALL/g' /etc/sudoers && \
    sed -i 's/#en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/g' /etc/locale.gen && \
    echo "LANG=en_US.UTF-8" > /etc/locale.conf && \
    locale-gen

RUN useradd -m -G wheel -s /bin/zsh user
USER user
WORKDIR /home/user
RUN git clone https://aur.archlinux.org/paru.git && \
    cd paru && \
    makepkg -sc
USER root
RUN pacman -U --noconfirm /home/user/paru/paru-*.pkg.tar.zst && \
    rm -rf /home/user/paru

# Install more dev tools
RUN paru -S --noconfirm base-devel gcc ccache cmake less

WORKDIR /root
RUN userdel -r user

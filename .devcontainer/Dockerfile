FROM mcr.microsoft.com/devcontainers/python:3.12

USER root

# Install gh cli 
RUN (type -p wget >/dev/null || (apt-get update && apt-get install wget fzf xclip -y )) \
&& mkdir -p -m 755 /etc/apt/keyrings \
&& out=$(mktemp) && wget -nv -O$out https://cli.github.com/packages/githubcli-archive-keyring.gpg \
&& cat $out | tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
&& chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
	&& mkdir -p -m 755 /etc/apt/sources.list.d \
	&& echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
	&& apt-get update \
	&& apt-get install gh -y

# Install dbt fusion
RUN curl -fsSL https://public.cdn.getdbt.com/fs/install/install.sh | bash -s -- --update



USER vscode

    
# Install mise
RUN curl https://mise.run | sh && /home/vscode/.local/bin/mise self-update -y


# Create cache folders
RUN mkdir -p /home/vscode/.vscode-server/extensions \
    && mkdir -p /home/vscode/.vscode-server/data/Machine \
    && mkdir -p /home/vscode/.vscode-server/bin \
	&& mkdir -p /home/vscode/.cache/semgrep \
    && mkdir -p /home/vscode/.config 
   

# Install ohmyzsh plugins
RUN git clone https://github.com/zsh-users/zsh-syntax-highlighting.git \
    ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting \
    && git clone https://github.com/zsh-users/zsh-history-substring-search.git \
    ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-history-substring-search

COPY --chown=vscode:vscode .zshrc /home/vscode/.zshrc

WORKDIR /workspaces

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python3 -c "import sys; sys.exit(0)" || exit 1
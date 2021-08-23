FROM continuumio/miniconda3
# 默认工作目录
ARG HOME=/root
WORKDIR $HOME
# 安装依赖
RUN pip install efinance

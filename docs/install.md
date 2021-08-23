## Installation

- 通过 `pip` 安装

```bash
pip install efinance
```

- 通过 `pip` 更新

```bash
pip install efinance --upgrade
```

- 通过 `docker` 安装

```bash
# 克隆代码
git clone https://github.com/Micro-sheep/efinance
# 切换工作目录为该项目的根目录
cd efinance
# 构建镜像(-t 指定构建后生成的镜像名称 . 指定 build 的对象是当前工作目录下的 dockerfile)
docker build -t efinance . --no-cache
# 以交互的方式运行镜像(运行之后自动删除容器,如不想删除 则可去掉 --rm)
docker run --rm -it efinance
```

- 源码安装（用于开发）

```bash
git clone https://github.com/Micro-sheep/efinance
cd efinance
pip install -e .
```

# Changelog

## v0.4.2(2022-03-07)

### Changed

- 扩展 `get_quote_history` 函数，支持通过设定 `kwargs` 来指定返回类型
  
### Added

- 为 `stock` 模块添加函数 `get_quote_snapshot` 以支持获取沪深市场 3 秒行情快照

---

## v0.4.0(2021-12-02)

### Fiexd

- 修复 fund 模块的命名错误以及其他 bug
  
### Added

- 添加对获取北证A股市场行情的支持

---

## v0.3.9(2021-10-23)

### Changed

- 优化 `fund` 模块的获取基金列表的函数
- 更新 `common` 模块的行情配置文件以支持获取更多板块的行情数据

### Added

- 添加获取指数成分股的函数 `efnance.stock.get_members`
- 增强函数 `efnance.stock.get_realtime_quotes`
- 添加获取企业 IPO 审核情况的函数 `efnance.stock.get_latest_ipo_info`
- 为搜索缓存添加过期时间
- 增强获取股东户数变动情况的函数 `efnance.stock.get_latest_holder_number`

---

## v0.3.8(2021-09-18)

### Changed

- 为 `fund` 模块的获取实时基金涨幅估计函数添加更多字段

### Added

- 添加获取多个板块成分股实时行情以及板块历史行情的功能
- 添加获取 ETF、LOF 基金实时行情的功能

## v0.3.7(2021-08-30)

### Added

- 添加使用 `docker` 安装的方法说明
- 添加获取沪深 A 股股东数量的功能
- 为 `stock` 模块添加龙虎榜数据获取功能

### Fixed

- 修复 `fund` 模块获取基金代码的函数产生的 bug
- 修复 `fund` 模块中获取基金涨幅估计函数产生的 bug

### Changed

- 为函数 `efinance.stock.get_all_company_performance` 添加更多字段

## v0.3.6 (2021-08-21)

### Fixed

- 修复创建缓存文件夹出错的问题

### Changed

- 简化部分代码

### Added

- 为 `futures` 模块添加实时行情获取功能

---

## v0.3.5 (2021-08-15)

### Added

- 添加沪深市场股票季度业绩表现数据获取功能
- 为股票实时行情数据添加更多字段
- 新增 `common` 模块，抽取出 `bond` 与 `stock` 的共同点放到其中
- 为 `bond` 模块添加获取历史单子流入数据获取的功能
- 添加更多的函数装饰器

---

## v0.3.4 (2021-08-08)

### Changed

- 修改部分注释文档缩进等级，优化其在 `vscode` 中的显示效果

---

## v0.3.3 (2021-08-08)

### Changed

- 修改项目文档主页链接

---

## v0.3.2 (2021-08-08)

### Added

- 使用 `sphinx` 构建文档
- 使用 read the docs 托管文档

---

## v0.3.1 (2021-08-05)

### Added

- 添加 session 机制

### Fixed

- 修复十大流通股东数据接口

---

## v0.3.0 (2021-08-03)

### Added

- 添加搜索结果缓存机制
- 引用 `jsonpath` 来解析数据

### Fixed

- 修复股票、债券实时行情接口表头错误（误把最高价写成最新价格）

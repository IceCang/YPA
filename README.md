# YPA
Yur PaintBoard AutoPaint Tool!

## Usage:

tokens.txt: **将 Token 一行一个放进去。**

config.json: **按例子将图片信息写入，图片与脚本在同一目录下。**

## Commands:

在加载结束后可，前缀为 ``:!``。

1. ``reload_board``: 重新加载版面

2. ``mode_sleep <sec:float>``: 设置间隔

``sec`` 为绘画队列刷新间隔**秒**数

3. ``shuffle <sf:bool>``: 设置 shuffle

``sf`` 为是否随机绘画

## Examples

tokens.txt Example:

```
2
abc
bdf
```


config.json Example:

```json
{"images":[{"x":0,"y":0,"path":"IMG.jpg"}]}
```

```json
{"images":[{"x":0,"y":0,"path":"IMG.jpg"},{"x":100,"y":100,"path":"IMG1.jpg"}]}
```


**注：只可使用 JPG 格式来存储图片。**

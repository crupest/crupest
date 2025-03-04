---
title: "Use PaddleOCR"
date: 2022-11-30T13:25:36+08:00
description: Simple steps to use PaddleOCR.
categories: coding
tags:
  - AI
  - python
  - OCR
---

I guess [_OCR_](https://en.wikipedia.org/wiki/Optical_character_recognition) is not something new for us. While there are a lot of open source artificial intelligence engines to achieve this, I need a easy-to-use one.

Recently I got a task to convert images into text. The image number is fairly big. So it's just impossible to OCR them one by one manually. So I wrote a python script to handle this tedious task.

<!--more-->

## Basic Processing

The original images contain a identical useless frame around the part that I need. So a crop is required because it will improve the performance (of course, the image is smaller) and there are unrelated texts in the frame.

Cropping is a easy problem. Just install [`Pillow`](https://pillow.readthedocs.io/en/stable/) package with `pip`:

```shell
pip install Pillow
```

Then use `Pillow` to do the cropping:

```python
image_file_list = ["image1.png", "image2.png", ...]
crop_file_list = [f"crop-{image_file}" for image_file in image_file_list]

## left, top, width, height
geometry = (100, 200, 300, 400)
print("Target geometry:", geometry)
## convert to (left, top, right, bottom)
geometry_ltrb = (geometry[0], geometry[1], geometry[0] +
                 geometry[2], geometry[1] + geometry[3])

## crop image with geometry
for index, image_file in enumerate(image_file_list):
    print(f"[{index + 1}/{len(image_file_list)}] Cropping '{image_file}' ...")
    with Image.open(join(dir_path, image_file)) as image:
        image.crop(geometry_ltrb).save(crop_file_list)
```

Now we have cropped images with original filename prefixed by `crop-`.

## Install PaddlePaddle

It's not easy to install [`PaddlePaddle`](https://github.com/PaddlePaddle/Paddle) with `pip` because it needs to run some native compilation. `Anaconda` is also complex to install and generates a lot of garbage files. The cleanest way is to use [`Docker`](https://www.docker.com) and with [`vscode` Remote Connect extensions](https://code.visualstudio.com/docs/devcontainers/containers).

Of course you need to install docker first, which is basically out of this blog's scope.

Then run the following command to create and run the `PaddlePaddle` image:

```shell
docker run -it --name ppocr -v "$PWD:/data" --network=host registry.baidubce.com/paddlepaddle/paddle:2.4.0-cpu /bin/bash
```

Something to note

1. You can change the mounted volumes to what you want to process.

2. This image is pulled from [`Baidu`](https://baidu.com) (the company creates _PaddlePaddle_) registry, which is fast in China. You can also pull it from `DockerHub`.

3. This image's _PaddlePaddle_ is based on cpu. Of course you have a cpu in your computer. But if you have a GPU or even [_CUDA_](https://developer.nvidia.com/cuda-downloads), you can select another image with correct tag. But cpu image is almost always work and using GPU is harder to configure.

4. I don't known why `--network=host` is needed. The container does not publish any ports. But it can access Internet faster or VSCode Remote Connect needs it?

## Install PaddleOCR

This image above only contain _PaddlePaddle_. [_PaddleOCR_](https://github.com/PaddlePaddle/PaddleOCR) is another package based on it  and needs individual install. However, this time we can just use `pip` again.

```shell
pip install paddleocr
```

## Coding

The next step is to write python codes. Also the easiest part!
You can connect to the container you just created with vscode and then happy coding!

```python
ocr = PaddleOCR(use_angle_cls=True, lang="ch") ## change the language to what you need
image_text_list = []
for index, crop_image_file in enumerate(crop_file_list):
    print(f"[{index + 1}/{len(crop_file_list)}] OCRing '{crop_image_file}' ...")
    result = ocr.ocr(crop_image_file, cls=True)
    result = result[0] ## There is some inconsistence of official docs. Result is a list with single element.
    line_text_list = [line[1][0] for line in result] ## a list of text str
    image_text = "\n".join(line_text_list)
    image_text_list.append(paragraph)
```

Now you can do any other things to the the `image_text_list` .

## Finally

Now just run the script. Or even better, customize it.

By the way, `PaddleOCR` is far more accurate than [`tesseract`](https://tesseract-ocr.github.io) in __Chinese__. Maybe because it is created by _Baidu_, a Chinese local company or I missed some configuration. For English, I haven't tested.

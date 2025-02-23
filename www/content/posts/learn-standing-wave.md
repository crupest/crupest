---
title: "学习驻波"
date: 2020-11-22T17:38:08+08:00
categories: 学习
tags:
  - 物理
description: 一个简单的驻波的笔记（划掉，LaTeX练习）。
enableMathJax: true
draft: true
---

## 前言

因为旷了几节大物课，直接导致了我知识脱节。在我不断的追赶之后，我终于慢慢赶上了进度。借这篇文章的机会学习一下驻波。如果写错了，请举报我！

其实我只是想玩一下 $\LaTeX$ .

### 介绍

**驻波**是指质元在平衡位置振动的波，它与**行波**相对。我个人的理解就是它不会跑，就在原地振动。

一种产生条件是，两列**振幅相同**，在同一直线上，沿**相反**方向传播的相干波叠加在一起就会产生。

### 数学推导

首先，沿 $Ox$ 轴正方向传播的波 1
$$y_1 = A \cos 2 \pi \left( \frac{t}{T} - \frac{x}{\lambda} \right)$$

然后，沿 $Ox$ 轴负方向传播的波 2
$$y_2 = A \cos 2 \pi \left( \frac{t}{T} + \frac{x}{\lambda} \right)$$

加起来
$$y = y_1 + y_2 = A\left[\cos2\pi\left(\frac{t}{T}-\frac{x}{\lambda}\right)+\cos2\pi\left( \frac{t}{T} + \frac{x}{\lambda} \right)\right]$$

使用**怎么都记不住**的和差化积公式
$$\cos\alpha+\cos\beta=2\cos\frac{\alpha+\beta}{2}\cos\frac{\alpha-\beta}{2}$$

就得到
$$y=\left(2A\cos\frac{2\pi}{\lambda}x\right)\cos\frac{2\pi}{T}t$$

对于任意的$x$，$\left(2A\cos\frac{2\pi}{\lambda}x\right)$是个定值，所以该点上的质元做简谐运动。

对于 $x=k\frac{\lambda}{2}\quad\left(k\in Z\right)$ 的质元
$$y=\pm2A\cos\frac{2\pi}{T}t$$
振幅最大，称为**波腹**。

而对于 $x=\left(2k+1\right)\frac{\lambda}{4}\quad\left(k\in Z\right)$ 的质元
$$y=0$$
也就是说它们不振动，称为**波节**。

## 最后

大部分公式copy自《普通物理学》。

好吧，我承认我其实就是把那本书上的公式搬运了过来。

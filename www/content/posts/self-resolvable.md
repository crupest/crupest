---
title: "Self Resolvable"
date: 2019-06-30T18:21:30+08:00
lastmod: 2019-07-23T23:57:35+08:00
categories: Coding
tags:
  - C++
  - CruUI
description: 一个 C++ 设计中的生命周期小工具。
draft: true
---

我实在是不知道怎么把这个东西翻译成中文。

任何事物的发明都有其起源。最近我在写我的那个 UI 库的时候发现了一个问题：

每当我的某个控件改变一个关系到布局的属性时，我就必须得重新 Layout，但是如果在某一个消息的处理过程中，用户改变了两个这样的属性，那么就有可能会连续 Layout 两次，很明显前一次的 Layout 是不必要的。所以我就改成了每需要 Layout 的时候，就把 layout 设成脏的，然后再投递一个事件，在下一个消息循环 Layout，这样，即使用户连续改了两个属性，Layout 的消息也只投递了一次，只会进行一次 Layout。

这样改了之后看似没有问题，但实际上又引入了一个潜在的 bug：万一用户改了两个属性之后又立即销毁了那个需要重新 Layout 的窗口呢？虽然说，好的写法应该是用户调用 InvokeLater 在下一个消息循环销毁窗口，但你不能对用户的行为做任何假定。于是，就需要在 Layout 消息处理中在真正 Layout 之前要判断一下窗口还在不在。

自然的去想，我就需要一个独立于窗口之外的一个变量来存储这个窗口是否被销毁了，但这样感觉很麻烦，我想把这个属性直接写到窗口里面，于是就产生了这个叫做 self-resolvable 的东西。

大致思路就是，有这个需要的对象应该提供一个接口`CreateResolver`，调用这个接口你就能获得一个`Resolver`，而这个`Resolver`又有一个接口`Resolve`，如果对象还在，那么调用它就返回这个对象，不然就返回`null`。这样会很方便，因为所有的这些都是写在对象里面的，不需要在对象外面写额外的逻辑，而且上述的情况肯定不会只出现一次，如果我们把它抽象出来，那么就能一劳永逸。

当然，我不会是第一个产生这种想法的人。实际上很多地方已经有了这个想法和实现。

比如 Qt，我记得 Qt 里的`QObject`都有一个销毁事件，在这个对象被销毁的时候，会发出一个信号。Qt 我不是很熟悉，但是这个功能对于写 UI 来说还是很有用的。

我不使用 Qt，但实际上，C++标准库已经有了这个想法的实现，而且功能比我说的更强大。那就是[`std::enable_shared_from_this`](https://en.cppreference.com/w/cpp/memory/enable_shared_from_this)。继承了这个类之后呢，你就可以随时从一个对象上调用`shared_from_this`获取一个`shared_ptr`，从而保证这个对象不会被销毁。如果你想要一个弱引用，那就可以调用一个`weak_from_this`来获取一个`weak_ptr`，但这个功能在 C++17 以后才有。标准库的这个功能，我也不是很熟悉，也从来没用过。

最终我还是选择自己撸一套简陋的工具，来实现我的想法。

```cpp
#include <iostream> // for test output
#include <cassert> // for assert
#include <memory> //for shared_ptr

//forward declaration
template <typename T>
class SelfResolvable;

template <typename T>
class ObjectResolver {
  friend SelfResolvable<T>;

 private:
  ObjectResolver(const std::shared_ptr<T*>& resolver) : resolver_(resolver) {}

 public:
  ObjectResolver(const ObjectResolver&) = default;
  ObjectResolver& operator=(const ObjectResolver&) = default;
  ObjectResolver(ObjectResolver&&) = default;
  ObjectResolver& operator=(ObjectResolver&&) = default;
  ~ObjectResolver() = default;

  T* Resolve() const {
    // resolver_ is null only when this has been moved.
    // You shouldn't resolve a moved resolver. So assert it.
    assert(resolver_);
    return *resolver_;
  }

 private:
  std::shared_ptr<T*> resolver_;
};

template <typename T>
class SelfResolvable {
 public:
  SelfResolvable() : resolver_(new T*(static_cast<T*>(this))) {}
  SelfResolvable(const SelfResolvable&) = delete;
  SelfResolvable& operator=(const SelfResolvable&) = delete;
  SelfResolvable(SelfResolvable&&) = delete;
  SelfResolvable& operator=(SelfResolvable&&) = delete;
  virtual ~SelfResolvable() { (*resolver_) = nullptr; }

  ObjectResolver<T> CreateResolver() { return ObjectResolver<T>(resolver_); }

 private:
  std::shared_ptr<T*> resolver_;
};

class O : public SelfResolvable<O> {};

int main() {
  const auto o = new O;
  const auto resolver = o->CreateResolver();
  std::cout << (resolver.Resolve() == o) << std::endl;
  delete o;
  std::cout << (resolver.Resolve() == nullptr) << std::endl;
  return 0;
}
```

代码的核心思想，就是创建一个`shared_ptr<T*>`，让所有的`ObjectResolver`都保存这个`shared_ptr`，而需要这个功能的类继承`SelfResolvable<T>`，在构造的时候把这个`shared_ptr`所包含的指针设为`this`，在销毁的时候把它设为`nullptr`。这样`ObjectResolver`只需要通过这个指针就能获取到这个对象的存在状态以及对象本身。

`ObjectResolver`是可以随意拷贝和移动的，而且我们只需要把对应的方法设为默认就可以了，因为它只包含一个`shared_ptr`成员。关键就是，在`Resolve`方法里面要判断一下`shared_ptr`本身是不是 null，如果是，说明这个`ObjectResolver`是被移动过的，那么用户就不应该使用它，因为不能使用一个移动过的对象，这是由使用者来保证的，我们只需要加一个断言来帮助解决这个可能发生的 bug（实际上我在第一次使用时就发生了这个问题）。

而`SelfResolvable`是既不可以拷贝也不可以移动，这是我故意设置的，因为我压根就没打算让继承它的类拷贝和移动（比如窗口）。而且这个类的拷贝和移动语义设计起来也会比较复杂，因为我暂时用不上，所以就不过度设计了。

最后有一点有趣的是，这里用到了一个叫做[curiously recurring template pattern](https://en.wikipedia.org/wiki/Curiously_recurring_template_pattern)的东西，具体的可以去看看维基，就不赘述了。

## Update 1

修改了所有的 Typo.

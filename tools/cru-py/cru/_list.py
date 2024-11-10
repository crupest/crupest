

class CruInplaceList(CruList, Generic[_V]):

    def clear(self) -> "CruInplaceList[_V]":
        self.clear()
        return self

    def extend(self, *l: Iterable[_V]) -> "CruInplaceList[_V]":
        self.extend(l)
        return self

    def reset(self, *l: Iterable[_V]) -> "CruInplaceList[_V]":
        self.clear()
        self.extend(l)
        return self

    def transform(self, *f: OptionalElementTransformer) -> "CruInplaceList"[Any]:
        return self.reset(super().transform(*f))

    def transform_if(
        self, f: OptionalElementTransformer, p: ElementPredicate[_V]
    ) -> "CruInplaceList"[Any]:
        return self.reset(super().transform_if(f, p))

    def remove_by_indices(self, *index: int) -> "CruInplaceList"[_V]:
        return self.reset(super().remove_by_indices(*index))

    def remove_all_if(self, p: ElementPredicate[_V]) -> "CruInplaceList"[_V]:
        return self.reset(super().remove_all_if(p))

    def remove_all_value(self, *r: Any) -> "CruInplaceList"[_V]:
        return self.reset(super().remove_all_value(*r))

    def replace_all_value(
        self, old_value: Any, new_value: R
    ) -> "CruInplaceList"[_V | R]:
        return self.reset(super().replace_all_value(old_value, new_value))

    @staticmethod
    def make(l: CanBeList[_V]) -> "CruInplaceList"[_V]:
        return CruInplaceList(ListOperations.make(l))



K = TypeVar("K")


class CruUniqueKeyInplaceList(Generic[_V, K]):
    KeyGetter = Callable[[_V], K]

    def __init__(
        self, get_key: KeyGetter, *, before_add: Callable[[_V], _V] | None = None
    ):
        super().__init__()
        self._get_key = get_key
        self._before_add = before_add
        self._l: CruInplaceList[_V] = CruInplaceList()

    @property
    def object_key_getter(self) -> KeyGetter:
        return self._get_key

    @property
    def internal_list(self) -> CruInplaceList[_V]:
        return self._l

    def validate_self(self):
        keys = self._l.transform(self._get_key)
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate keys!")

    def get_or(self, k: K, fallback: Any = CRU_NOT_FOUND) -> _V | Any:
        r = self._l.find_if(lambda i: k == self._get_key(i))
        return r if r is not CRU_NOT_FOUND else fallback

    def get(self, k: K) -> _V:
        v = self.get_or(k, CRU_NOT_FOUND)
        if v is CRU_NOT_FOUND:
            raise KeyError(f"Key not found!")
        return v

    def has_key(self, k: K) -> bool:
        return self.get_or(k, CRU_NOT_FOUND) is not CRU_NOT_FOUND

    def has_any_key(self, *k: K) -> bool:
        return self._l.any(lambda i: self._get_key(i) in k)

    def try_remove(self, k: K) -> bool:
        i = self._l.find_index_if(lambda v: k == self._get_key(v))
        if i is CRU_NOT_FOUND:
            return False
        self._l.remove_by_indices(i)
        return True

    def remove(self, k: K, allow_absense: bool = False) -> None:
        if not self.try_remove(k) and not allow_absense:
            raise KeyError(f"Key {k} not found!")

    def add(self, v: _V, /, replace: bool = False) -> None:
        if self.has_key(self._get_key(v)):
            if replace:
                self.remove(self._get_key(v))
            else:
                raise ValueError(f"Key {self._get_key(v)} already exists!")
        if self._before_add is not None:
            v = self._before_add(v)
        self._l.append(v)

    def set(self, v: _V) -> None:
        self.add(v, True)

    def extend(self, l: Iterable[_V], /, replace: bool = False) -> None:
        if not replace and self.has_any_key([self._get_key(i) for i in l]):
            raise ValueError("Keys already exists!")
        if self._before_add is not None:
            l = [self._before_add(i) for i in l]
        keys = [self._get_key(i) for i in l]
        self._l.remove_all_if(lambda i: self._get_key(i) in keys).extend(l)

    def clear(self) -> None:
        self._l.clear()

    def __iter__(self):
        return iter(self._l)

    def __len__(self):
        return len(self._l)

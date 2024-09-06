local function remove_element(tbl, element)
    local index = nil
    for i, v in ipairs(tbl) do
        if element == v then
            index = i
            break
        end
    end
    if index then
        table.remove(tbl, index)
    end
    return tbl
end

local function element_at(tbl, element)
    local at = nil
    for i, v in ipairs(tbl) do
        if element == v then
            at = i
            break
        end
    end
    return at
end

local function includes(tbl, element)
    for _, v in ipairs(tbl) do
        if v == element then return true end
    end
    return false
end

local function string_start_with(str, prefix)
    return string.find(str, prefix, 0, true) == 1
end

return {
    remove_element = remove_element,
    element_at = element_at,
    includes = includes,
    string_start_with = string_start_with,
}

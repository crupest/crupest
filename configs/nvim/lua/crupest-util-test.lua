local test_tsx_path = "~/codes/Timeline/FrontEnd/src/index.tsx"

local util = loadfile("./lua/crupest-util.lua")()

print(util.find_npm_exe(test_tsx_path, "eslint"))


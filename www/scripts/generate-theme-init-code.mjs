import { join } from "node:path";

import { transformFile } from "@swc/core";

const output = await transformFile(
    join(import.meta.dirname, "theme-init-code.js"),
    {
        minify: true,
        jsc: {
            minify: {
                compress: true,
                mangle: true,
            },
        },
    },
);
console.log(`(()=>{${output.code}})()`);

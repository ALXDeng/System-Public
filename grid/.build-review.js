const fs=require("fs");const [,,srcF,tF,outF]=process.argv;const src=fs.readFileSync(srcF,"utf8").split("\n");
if(!src[290].startsWith("const DATA")||!src[291].startsWith("const EXTRA"))throw "lines moved";
fs.writeFileSync(outF,fs.readFileSync(tF,"utf8").replace("/*__DATA__*/",()=>src.slice(290,292).join("\n")));

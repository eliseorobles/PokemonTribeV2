import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setCodec("h264");
Config.setPixelFormat("yuv420p");
Config.setJpegQuality(92);
Config.setConcurrency(null); // auto — uses all available cores
Config.setEntryPoint("src/index.ts");

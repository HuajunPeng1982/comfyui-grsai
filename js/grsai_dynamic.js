import { app } from "../../../scripts/app.js";

const SIZE_MAP = {
    "gpt-image-2-vip": {
        "1:1": ["1024x1024", "2048x2048", "2880x2880"],
        "16:9": ["1280x720", "2048x1152", "3840x2160"],
        "9:16": ["720x1280", "1152x2048", "2160x3840"],
        "4:3": ["1152x864", "2304x1728", "3264x2448"],
        "3:4": ["864x1152", "1728x2304", "2448x3264"],
        "3:2": ["1536x1024", "2048x1360", "3504x2336"],
        "2:3": ["1024x1536", "1360x2048", "2336x3504"],
        "5:4": ["1120x896", "2240x1792", "3200x2560"],
        "4:5": ["896x1120", "1792x2240", "2560x3200"],
        "21:9": ["1456x624", "2912x1248", "3840x1648"],
        "9:21": ["624x1456", "1248x2912", "1648x3840"],
        "1:3": ["688x2048", "1280x3840"],
        "3:1": ["2048x688", "3840x1280"],
        "2:1": ["1536x768", "3072x1536", "3840x1920"],
        "1:2": ["768x1536", "1536x3072", "1920x3840"],
    },
    "gpt-image-2": {
        "1:1": ["1024x1024"],
        "16:9": ["1672x941"],
        "9:16": ["941x1672"],
        "4:3": ["1443x1090"],
        "3:4": ["1090x1443"],
        "3:2": ["1536x1024"],
        "2:3": ["1024x1536"],
        "5:4": ["1408x1120"],
        "4:5": ["1120x1408"],
        "21:9": ["1920x832"],
        "9:21": ["832x1920"],
        "1:2": ["896x1792"],
        "2:1": ["1792x896"],
    },
};

// All ratios for each model
const RATIOS_BY_MODEL = {
    "gpt-image-2-vip": Object.keys(SIZE_MAP["gpt-image-2-vip"]),
    "gpt-image-2": Object.keys(SIZE_MAP["gpt-image-2"]),
};

app.registerExtension({
    name: "comfyui-grsai.dynamic",
    async nodeCreated(node) {
        if (node.comfyClass !== "GrsaiImageGenerate") return;

        const modelWidget = node.widgets.find((w) => w.name === "model");
        const ratioWidget = node.widgets.find((w) => w.name === "aspect_ratio");
        const sizeWidget = node.widgets.find((w) => w.name === "image_size");

        if (!modelWidget || !ratioWidget || !sizeWidget) return;

        const updateSizes = () => {
            const model = modelWidget.value;
            const ratio = ratioWidget.value;
            const sizes = SIZE_MAP[model]?.[ratio] || ["1024x1024"];
            sizeWidget.options.values = sizes;
            if (!sizes.includes(sizeWidget.value)) {
                sizeWidget.value = sizes[0];
            }
            sizeWidget.options.values = sizes;
            node.setDirtyCanvas(true, true);
        };

        const updateRatios = () => {
            const model = modelWidget.value;
            const ratios = RATIOS_BY_MODEL[model] || Object.keys(SIZE_MAP["gpt-image-2"]);
            ratioWidget.options.values = ratios;
            if (!ratios.includes(ratioWidget.value)) {
                ratioWidget.value = ratios[0];
            }
            ratioWidget.options.values = ratios;
            // After changing ratios, also update sizes
            updateSizes();
        };

        // Save original callbacks and chain them
        const origModelCb = modelWidget.callback;
        modelWidget.callback = function (val) {
            if (origModelCb) origModelCb.call(this, val);
            updateRatios();
        };

        const origRatioCb = ratioWidget.callback;
        ratioWidget.callback = function (val) {
            if (origRatioCb) origRatioCb.call(this, val);
            updateSizes();
        };
    },
});

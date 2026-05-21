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

const RATIOS_BY_MODEL = {
    "gpt-image-2-vip": Object.keys(SIZE_MAP["gpt-image-2-vip"]),
    "gpt-image-2": Object.keys(SIZE_MAP["gpt-image-2"]),
};

const PRESET_KEYS = {
    "gpt-image-2-vip (内置)": "sk-3953625ea3f64df593980dbfde5f93d0",
    "gpt-image-2 (内置)": "sk-3e09bb0bd5d541b2b6e9e683d08e74fd",
};

function setComboValues(widget, values) {
    widget.options.values.length = 0;
    for (const v of values) {
        widget.options.values.push(v);
    }
    if (!values.includes(widget.value)) {
        widget.value = values[0];
    }
}

function setupNode(node) {
    if (node.comfyClass !== "GrsaiImageGenerate") return;

    const modelW = node.widgets.find((w) => w.name === "model");
    const ratioW = node.widgets.find((w) => w.name === "aspect_ratio");
    const sizeW = node.widgets.find((w) => w.name === "image_size");
    const presetW = node.widgets.find((w) => w.name === "api_key_preset");
    const keyW = node.widgets.find((w) => w.name === "api_key");

    if (!modelW || !ratioW || !sizeW || !presetW || !keyW) return;

    function updateSizes() {
        const model = modelW.value;
        const ratio = ratioW.value;
        const sizes = SIZE_MAP[model]?.[ratio] || ["1024x1024"];
        setComboValues(sizeW, sizes);
    }

    function updateRatios() {
        const model = modelW.value;
        const ratios = RATIOS_BY_MODEL[model] || Object.keys(SIZE_MAP["gpt-image-2"]);
        setComboValues(ratioW, ratios);
        updateSizes();
    }

    function updateKey() {
        const preset = presetW.value;
        if (preset === "其它") return;
        const key = PRESET_KEYS[preset];
        if (key && keyW.value !== key) {
            keyW.value = key;
        }
    }

    // Hook model changes → update ratios + sizes
    const origModelCb = modelW.callback;
    modelW.callback = function (v, ...args) {
        if (origModelCb) origModelCb.call(this, v, ...args);
        updateRatios();
        node.setDirtyCanvas(true, true);
    };

    // Hook ratio changes → update sizes
    const origRatioCb = ratioW.callback;
    ratioW.callback = function (v, ...args) {
        if (origRatioCb) origRatioCb.call(this, v, ...args);
        updateSizes();
        node.setDirtyCanvas(true, true);
    };

    // Hook preset changes → update key
    const origPresetCb = presetW.callback;
    presetW.callback = function (v, ...args) {
        if (origPresetCb) origPresetCb.call(this, v, ...args);
        updateKey();
        node.setDirtyCanvas(true, true);
    };

    // Apply initial filtering
    updateRatios();
    updateKey();
}

// Register via beforeRegisterNodeDef (ComfyUI standard hook)
app.registerExtension({
    name: "comfyui-grsai.dynamic",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "GrsaiImageGenerate") return;
        const orig = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = orig ? orig.apply(this, arguments) : undefined;
            setupNode(this);
            return r;
        };
    },
});

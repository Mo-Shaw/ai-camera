# -*- coding: utf-8 -*-
"""
📷 AI摄影教练 app端 V2.7.3
变更：删除镜像功能（归位给camera.html取景器）
     新增"先去取景器看参数"动线引导
"""

import base64
import io
from openai import OpenAI
from PIL import Image, ImageDraw
import streamlit as st

VIEWER_URL = "https://mo-shaw.github.io/ai-camera/camerav2.7.html"  # 取景器地址

# ============================================================
# 画图工具
# ============================================================
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def draw_grid(img, line_color=(255, 80, 80), width=4):
    img = img.convert("RGB")
    w, h = img.size
    draw = ImageDraw.Draw(img)
    xs = [w // 3, 2 * w // 3]
    ys = [h // 3, 2 * h // 3]
    for x in xs:
        draw.line([(x, 0), (x, h)], fill=line_color, width=width)
    for y in ys:
        draw.line([(0, y), (w, y)], fill=line_color, width=width)
    for x in xs:
        for y in ys:
            r = width * 3
            draw.ellipse([x - r, y - r, x + r, y + r], fill=(255, 215, 0))
    return img

# ============================================================
# AI调用
# ============================================================
REVIEW_PROMPT = """# 角色
你是专业摄影教练，服务摄影新手。用户已经拍好照片，请点评。

# 输出格式（严格遵守）
📷 场景识别：
✅ 照片优点：
⚠️ 构图问题：
🎯 参数方向：（只写光圈/快门/ISO/白平衡，不写构图）
💡 一句话总结：

# 规则
- 建议具体到动作，禁止空话
- 先肯定再指出问题"""

SCOUT_PROMPT = """# 角色
你是手机摄影侦察顾问。用户刚到一个陌生地点，拍了一张环境广域图，
不知道这里哪里值得拍、站在哪拍。请分析并推荐机位。

# 任务
1. 扫描画面：找出有潜力的元素（建筑/树木/光影/线条/人物活动等）
2. 推荐2-3个拍摄机位，每个包含：
   - 站位：相对画面中标志物的具体位置
   - 朝向：朝哪个方向、拍什么主体
   - 效果：一句话想象拍出来的样子
3. 光线评估：现在适合拍什么风格？是否值得等黄金时刻？
4. 避坑：指出画面中不适合拍的地方及原因

# 输出格式
🗺️ 场景亮点：
📍 机位1：
  · 站位：
  · 朝/拍：
  · 效果：
📍 机位2：
  · 站位：
  · 朝/拍：
  · 效果：
⏰ 光线建议：
⚠️ 避坑：

# 规则
- 站位描述必须具体可执行（"走到画面左侧那棵大树旁，蹲低朝桥拍"）
- 充分利用前景、框架、引导线等构图元素
- 画面实在没可拍性就诚实说，并给出替代建议（如拍光影特写）"""

def ask_ai(api_key, image_bytes, model, system_prompt):
    client = OpenAI(api_key=api_key, base_url="https://open.bigmodel.cn/api/paas/v4/")
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "text", "text": "请看这张照片"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
            ]}
        ]
    )
    return resp.choices[0].message.content

# ============================================================
# 界面
# ============================================================
st.set_page_config(page_title="AI摄影教练", page_icon="📷")
st.title("📷 AI摄影教练")
st.caption("🔍找机位 → 👁取景器摆位 → 自带相机拍 → 📁上传点评")

with st.sidebar:
    st.header("⚙️ 设置")
    api_key = st.text_input("智谱API Key", type="password",
                            help="bigmodel.cn 免费申请，sk-开头")
    model = st.selectbox("视觉模型", ["glm-4v-flash", "glm-4v", "glm-4.5v"])
    color_hex = st.color_picker("网格颜色", "#FF5050")
    st.divider()
    st.caption("免费额度用完会报错，第二天自动恢复")

# ★ Key引导横幅
if not api_key:
    st.warning("🔑 **第一次用？先花2分钟领一把钥匙：** 浏览器打开 **bigmodel.cn** → 注册登录 → 控制台找「API Keys」→ 创建 → 复制 **sk-开头** 的那串字符 → 填到**左侧栏**。")

# ★ 新增：正确动线引导（拍前去取景器看参数，拍完回来点评）
st.info("💡 **推荐流程：① 先打开 [👁 取景器](" + VIEWER_URL + ") 看实时构图+ISO/快门建议 → ② 用手机自带相机正式拍 → ③ 回到本页上传点评。本页的「直接拍照」仅供临时应急，实时摆位请用取景器。")

tab_scout, tab_cam, tab_up = st.tabs(["🔍 找机位", "📸 直接拍照(应急)", "📁 上传点评"])

# ---------- 模式①：找机位 ----------
with tab_scout:
    st.info("到一个新地方？先拍张环境全景，AI告诉你哪里出片、站哪拍")
    wide = st.camera_input("拍一张这个地方的广域图")
    if wide:
        st.image(wide, width=300)
        if not api_key:
            st.warning("⚠️ 请先在左侧填API Key")
        else:
            with st.spinner("AI正在侦察这个地点…"):
                try:
                    report = ask_ai(api_key, wide.getvalue(), model, SCOUT_PROMPT)
                    st.subheader("🗺️ 机位侦察报告")
                    st.markdown(report)
                except Exception as e:
                    st.error(f"出错了：{e}")
                    st.info("检查Key / 额度 / 换模型名")

# ---------- 模式②：直接拍照（应急，已删镜像——镜像属于取景器） ----------
with tab_cam:
    st.markdown("**📸 拍照三步：① 允许摄像头 → ② 点「Take Photo」→ ③ 自动出网格+AI分析**")
    if "cam_id" not in st.session_state:
        st.session_state["cam_id"] = 0
    if st.button("🔄 重拍一张"):
        st.session_state["cam_id"] += 1
    camera_photo = st.camera_input("对准主体，点击下方按钮拍照",
                                   key=f"cam_{st.session_state['cam_id']}")
    if camera_photo:
        img = Image.open(camera_photo)
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("原图"); st.image(img, use_container_width=True)
        grid_img = draw_grid(img, hex_to_rgb(color_hex))
        with col2:
            st.subheader("三分法网格"); st.image(grid_img, use_container_width=True)
        if not api_key:
            st.warning("⚠️ 请先在左侧填API Key")
        else:
            with st.spinner("AI分析中，约10秒……"):
                try:
                    advice = ask_ai(api_key, camera_photo.getvalue(), model, REVIEW_PROMPT)
                    st.subheader("🧠 AI分析")
                    st.markdown(advice)
                    buf = io.BytesIO()
                    grid_img.save(buf, format="JPEG")
                    st.download_button("⬇️ 下载带网格的图", buf.getvalue(),
                                       "photo_with_grid.jpg", "image/jpeg")
                except Exception as e:
                    st.error(f"出错了：{e}")
                    st.info("检查Key / 额度 / 换模型名")

# ---------- 模式③：上传点评（主战场） ----------
with tab_up:
    st.markdown("**把你刚用自带相机拍好的照片传上来，AI给你逐条点评** 👇")
    up = st.file_uploader("选择照片（jpg/png）", type=["jpg", "jpeg", "png"])
    if up:
        img = Image.open(up)
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("原图"); st.image(img, use_container_width=True)
        grid_img = draw_grid(img, hex_to_rgb(color_hex))
        with col2:
            st.subheader("三分法网格"); st.image(grid_img, use_container_width=True)
        if not api_key:
            st.warning("⚠️ 请先在左侧填API Key")
        else:
            with st.spinner("AI分析中，约10秒……"):
                try:
                    advice = ask_ai(api_key, up.getvalue(), model, REVIEW_PROMPT)
                    st.subheader("🧠 AI分析")
                    st.markdown(advice)
                    buf = io.BytesIO()
                    grid_img.save(buf, format="JPEG")
                    st.download_button("⬇️ 下载带网格的图", buf.getvalue(),
                                       "photo_with_grid.jpg", "image/jpeg")
                except Exception as e:
                    st.error(f"出错了：{e}")
                    st.info("检查Key / 额度 / 换模型名")
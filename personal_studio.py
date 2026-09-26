"""A small local image library for Codex-assisted scientific figures."""

from __future__ import annotations

import streamlit as st

from personal_library import (
    CATEGORY_LABELS, add_reference, delete_reference, disk_usage,
    initialize, list_references, set_category,
)


st.set_page_config(page_title="KnowPlot 参考图库", page_icon="🎨", layout="wide")
initialize()

st.title("KnowPlot 参考图库")
st.caption("看到喜欢的论文图，就存进来并选一个类别。画图时 Codex 会直接看图，自己判断值得借鉴的设计。")

uploaded = st.file_uploader(
    "添加图片", type=["png", "jpg", "jpeg", "webp"],
    accept_multiple_files=True, help="可以一次选择多张同类别图片。",
)
category = st.selectbox("归入哪一类？", list(CATEGORY_LABELS),
                        format_func=CATEGORY_LABELS.get)
if st.button("加入图库", type="primary", disabled=not uploaded):
    created = skipped = 0
    try:
        for file in uploaded:
            _, is_new = add_reference(file.getvalue(), file.name,
                                      figure_type=category)
            created += int(is_new)
            skipped += int(not is_new)
        st.success(f"已加入 {created} 张" + (f"，跳过重复图片 {skipped} 张" if skipped else ""))
        st.rerun()
    except Exception as exc:
        st.error(f"图片导入失败：{exc}")

rows = list_references()
st.divider()
st.subheader(f"已收藏 {len(rows)} 张")
if not rows:
    st.info("先添加一张参考图。以后在当前 Codex 对话中说出你的绘图需求，我会从这里找合适的图并直接观察它。")
else:
    tabs = st.tabs([
        f"{label} · {sum(row['figure_type'] == key for row in rows)}"
        for key, label in CATEGORY_LABELS.items()
    ])
    for tab, (key, _) in zip(tabs, CATEGORY_LABELS.items()):
        with tab:
            category_rows = [row for row in rows if row["figure_type"] == key]
            if not category_rows:
                st.caption("这个类别还没有图片。")
            for offset in range(0, len(category_rows), 3):
                columns = st.columns(3)
                for column, row in zip(columns, category_rows[offset:offset + 3]):
                    with column:
                        st.image(row["thumb_path"], use_container_width=True)
                        st.caption(row["title"])
                        with st.expander("管理图片"):
                            new_category = st.selectbox(
                                "类别", list(CATEGORY_LABELS),
                                index=list(CATEGORY_LABELS).index(row["figure_type"]),
                                format_func=CATEGORY_LABELS.get,
                                key=f"category_{row['id']}",
                            )
                            if st.button("保存类别", key=f"save_{row['id']}"):
                                set_category(row["id"], new_category)
                                st.rerun()
                            if st.button("删除图片", key=f"delete_{row['id']}"):
                                delete_reference(row["id"])
                                st.rerun()

usage = disk_usage()["library"] / 1024 / 1024
st.caption(f"图库占用约 {usage:.1f} MB，图片保存在本机。")

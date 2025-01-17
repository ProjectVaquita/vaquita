# -*- coding:utf-8 -*-
"""
:Date: 2023-02-19 15:05:02
:LastEditTime: 2023-02-19 15:05:04
:Description: Optimize and comment the code
"""
from loguru import logger
import streamlit as st
from data_juicer.platform.src.utils.st_components import get_remote_ip
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data_juicer.utils.mm_utils import SpecialTokens
import os 
from collections import defaultdict
from data_juicer.utils.vis import plot_dups
from data_juicer.utils.mm_utils import remove_special_tokens
import numpy as np
from data_juicer.utils.constant import Fields, DEFAULT_PREFIX
import random


# Constants
IMAGE_KEY = "images"
TEXT_KEY = "text"
ISSUE_DICT = {
    '重复-图像重复': 'duplicate-image_deduplicator',
    '重复-文本重复': 'duplicate-document_deduplicator',
    '低信息-图像': 'cleanvision-is_low_information_issue',
    '不匹配-BLIP': 'filter-image_text_matching_filter',
    '不匹配-CLIP': 'filter-image_text_similarity_filter',
    '缺失-图像缺失': 'filter-image_validation_filter',
    '低质量-非英语': 'filter-language_id_score_filter',
    '低质量-字符重复': 'filter-character_repetition_filter',
    '低质量-词语重复': 'filter-word_repetition_filter',
    '低质量-图像模糊': 'cleanvision-is_blurry_issue',
    '低质量-图像极黑': 'cleanvision-is_dark_issue',
    '低质量-图像黑白': 'cleanvision-is_grayscale_issue',
    '低质量-图像极亮': 'cleanvision-is_light_issue',
    '低质量-图像比例1': 'filter-image_aspect_ratio_filter',
    '低质量-图像比例2': 'cleanvision-is_odd_aspect_ratio_issue',
    # '低质量-图像大小': 'cleanvision-is_odd_size_issue',
    # '低质量-图像大小2': 'filter-image_shape_filter',
    '优质数据': 'demo-processed'
}
CLEANLAB_ISSUE = ["is_odd_aspect_ratio_issue", 
                "is_low_information_issue", "is_light_issue", 
                "is_grayscale_issue", "is_dark_issue", "is_blurry_issue"]

# Main function to write data
def write():
    # Logging user details
    logger.info(f"enter doc page, user_name: {st.session_state['name']}, ip: {get_remote_ip()}")
    
    # Display title
    st.title('数据集报告')
    
    # Paths
    project_path = "./outputs/demo-backbone-opensource"
    tracer_path = f"{project_path}/trace"
    
    cleanlab_path = "%s/filter-cleanvision_mycleanlab.jsonl" % tracer_path
    if os.path.exists(cleanlab_path):
        filter_df = pd.read_json(cleanlab_path, lines=True)
        for issue in CLEANLAB_ISSUE:
            out_path = os.path.join(tracer_path, f'cleanvision-{issue}.jsonl')
            if not os.path.exists(out_path):
                tmp_df = filter_df[pd.DataFrame(filter_df[Fields.stats].tolist())[issue].apply(lambda x: True in x)]
                if not tmp_df.empty:
                    tmp_df.to_json(out_path,
                                orient='records',
                                lines=True,
                                force_ascii=False)
    
    # Load and calculate data
    stats_prob, stats_total = calculate_statistics(project_path)

    # Display speedometer chart
    display_speedometer_chart(stats_total)
    
    # Display pie chart
    display_pie_chart(stats_prob)
        
    # File paths
    file_paths = get_file_paths(tracer_path)
    
    # Problems dictionary
    problems_dict = {file_path.split('/')[-1].split('.')[0]: file_path for file_path in file_paths}
    
    # Remove unused items from ISSUE_DICT
    ISSUE_DICT_T = {key: val for key, val in ISSUE_DICT.items() if val in problems_dict.keys()}
        
    # Display section title
    st.markdown('<p class="big-font">数据清洗结果展示</p>', unsafe_allow_html=True)
    
    # Selectbox for choosing issue type
    category_issue = st.selectbox("选择错误类型", ISSUE_DICT_T.keys())
    amount = 3
    images_per_col = 3
    
    # Display selected data
    if category_issue:
        if category_issue == '优质数据':
            cat_df = "%s/demo-processed.jsonl" % project_path
        else:
            cat_df = problems_dict[ISSUE_DICT_T[category_issue]]
            
        selected_issues = read_random_lines(cat_df, amount)
        selected_rows = jsonl_to_dataframe(selected_issues)

        # selected_issues = pd.read_json(cat_df, lines=True)
        # selected_rows = selected_issues.sample(n=amount)
        
        cols = st.columns(images_per_col)
        if not category_issue.startswith('重复-'):
            for j, (index, row) in enumerate(selected_rows.iterrows()):
                images = row[IMAGE_KEY]
                text = remove_special_tokens(row[TEXT_KEY])
                if text == "haha" and row.get("type", None):
                    caption = '<p style="font-family:sans-serif; font-size: 24px;">%s</p>' % row.get("type", None)
                else:
                    caption = '<p style="font-family:sans-serif; font-size: 24px;">%s</p>' % text if len(text) < 30 else text[:30]
                cols[j].markdown(caption, unsafe_allow_html=True)
                cols[j].image(images, use_column_width=True)
        else:
            for j, (index, row) in enumerate(selected_rows.iterrows()):
                oris = row['ori']
                dup_num = row['dup_num']
                dups = [row[f"dup{_ + 1}"] for _ in range(dup_num)][:12]
                display_image = plot_dups(oris, dups, dup_num)
                cols[j].pyplot(display_image)


def read_random_lines(filename, num_lines=3):
    lines = []
    with open(filename, 'r', encoding='utf-8') as file:
        for line in file:
            lines.append(line)
    
    return random.sample(lines, num_lines)


def jsonl_to_dataframe(jsonl_lines):
    data = [json.loads(line) for line in jsonl_lines]
    return pd.DataFrame(data)


# Display pie chart
def display_pie_chart(stats):
    # Create pie chart
    tmp_stats = stats.copy()
    tmp_stats.pop("Clean")
    fig = px.pie(
        names=tmp_stats.keys(),
        values=tmp_stats.values(),
        title='问题类别图',
    )

    # Update text size
    fig.update_traces(textfont_size=20, hoverlabel_font_size=18)  # Adjust text size here
    fig.update_layout(
        autosize=False,
        width=800,  # Set the width of the chart
        height=600,  # Set the height of the chart
        legend=dict(font=dict(size=20)),  # Adjust legend font size here
        title=dict(font=dict(size=48))  # Adjust title font size here
    )

    # Display pie chart
    pie_chart = st.plotly_chart(fig, use_container_width=True)

# Display speedometer chart
def display_speedometer_chart(stats):
    # Create figure
    fig = go.Figure()
    score = 100 * stats["Clean"] / sum(stats.values())
    
    # Add trace
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "数据集数据点得分", 'font': {'size': 48}},
        gauge={
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "dodgerblue"},
            'bar': {'color': "dodgerblue"},
            'bgcolor': 'rgba(0,0,0,0)',  # Transparent background for the gauge
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 60], 'color': 'lightgray'},
                {'range': [60, 80], 'color': 'darkgray'},
                {'range': [80, 100], 'color': 'gray'}],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': score}
        },
        number={'font': {'size': 60, 'color': "dodgerblue"}}
    ))
    
    # Add text annotation
    fig.add_annotation(
        x=0.5,
        y=0.5,
        text="总数据量: %d <br>问题数据: %d <br>问题类别: %d" % (sum(stats.values()), sum(stats.values()) - stats["Clean"], len(stats) - 1),  # Change this to your desired text
        font=dict(size=16, color="white"),  # Customize font size and color
        showarrow=False,
        align="center"
    )
    
    # Set layout for transparency
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',  # Transparent background for the paper
        plot_bgcolor='rgba(0,0,0,0)',  # Transparent background for the plot
        font={'color': "dodgerblue", 'family': "Arial"}
    )

    # Display chart
    st.plotly_chart(fig, use_container_width=True)  

# Get file paths
def get_file_paths(folder_path):
    file_paths = []
    # Walk through all files and directories in the given folder
    for root, directories, files in os.walk(folder_path):
        for filename in files:
            # Join the root path and the file name to get the absolute file path
            file_paths.append(os.path.join(root, filename))
    return file_paths

# Calculate statistics
def calculate_statistics(project_path):
    tracer_path = f"{project_path}/trace"
    output_path = f"{project_path}/demo-processed.jsonl"

    # Function to get total line count
    def get_total_line_count(jsonl_file):
        with open(jsonl_file, 'r') as file:
            total_line_count = sum(1 for line in file)
        return total_line_count
    
    # Function to get total duplicate numbers
    def get_total_dup_nums(jsonl_file):
        total_dup_nums = 0
        with open(jsonl_file, 'r') as file:
            for line in file:
                json_obj = json.loads(line)
                dup_num = json_obj['dup_num']
                total_dup_nums += dup_num
        return total_dup_nums

    file_paths = get_file_paths(tracer_path)
    
    problems_dict, stats_dict_prob, stats_dict_total = {}, defaultdict(int), defaultdict(int)
    for file_path in file_paths:
        file_p = file_path.split('/')[-1].split('.')[0]
        typ = file_p.split('-')[0]
        problem = file_p.split('-')[-1].split(".")[0]
        
        if problem == "cleanvision_mycleanlab":
            stats_dict_total[problem] = get_total_line_count(file_path)
        elif typ == "duplicate":
            stats_dict_prob[problem] = get_total_dup_nums(file_path)
            stats_dict_total[problem] = get_total_dup_nums(file_path)
        elif typ == "filter" and problem.startswith("is"):
            stats_dict_total[problem] = get_total_line_count(file_path)
        else:
            stats_dict_prob[problem] = get_total_line_count(file_path)
        
        problems_dict[file_path] = problem
        
    stats_dict_prob["Clean"] = get_total_line_count(output_path)
    stats_dict_total["Clean"] = get_total_line_count(output_path)
    print(stats_dict_prob)
    print(stats_dict_total)

    return stats_dict_prob, stats_dict_total


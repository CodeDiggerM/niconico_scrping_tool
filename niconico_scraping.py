import streamlit as st
from st_aggrid import GridOptionsBuilder, AgGrid, JsCode
import base64
import seaborn as sns
import os
import japanize_matplotlib
import matplotlib.pyplot as plt
from PIL import Image
import pandas as pd
import pytz
import requests, random, string
import json
from datetime import datetime, timedelta
import time

TABLE_FONTSIZE = "17px"
HOME_PATH = "/mnt/data/Streamlit/moomin/%s"
RAKUTEN = "Rakuten"
AMAZON = "Amazon"
HOME_PATH = "./%s"
ICON_FILE = "niconico.png"
USER_INFO_FILE = "user_info.txt"

RESULT_FILE = HOME_PATH % "niconico_result.csv"
SHOW_COLS = ["text", "nicoruCount", "score", "time"]


def get_base64(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()


def set_background(png_file):
    bin_str = get_base64(png_file)
    page_bg_img = '''
    <style>
    .stApp {
    background-color: pink !important;
    background-image: url("data:image/png;base64,%s");
    background-size: cover;
    }
    </style>

    ''' % bin_str
    st.markdown(page_bg_img, unsafe_allow_html=True)


def set_up_page():
    im = Image.open(HOME_PATH % ICON_FILE)
    STREAMLIT_AGGRID_URL = "https://github.com/PablocFonseca/streamlit-aggrid"

    st.set_page_config(
        layout="centered",
        page_icon=im,
        page_title="NicoNico scraping"
    )
    st.title("NicoNico scraping Tool")
    set_background(HOME_PATH % 'niconico_lp.png')


def create_table(data, chart_type):
    gb = GridOptionsBuilder.from_dataframe(data)
    gb.configure_default_column(min_column_width=120,
                                suppressMenu=True,
                                autoSizeColumns=True,
                                editable=False)
    gb.configure_grid_options(enableRangeSelection=True)
    gb.configure_pagination(paginationPageSize=100, paginationAutoPageSize=False)
    if chart_type == "Daily Report":
        cellsytle_jscode = JsCode("""
            function(params) {
                params.columnApi.autoSizeColumns();
                if (params.data.Day == '月' ||
                    params.data.Day == '火' ||
                    params.data.Day == '水' ||
                    params.data.Day == '木' ||
                    params.data.Day == '金'
                ) {
                    return {
                        'color': 'black',
                        'backgroundColor': 'white',
                        'fontSize':'{fontSize}'
                    }
                } else if (
                    params.data.Day == '土' ||
                    params.data.Day == '日' )
                {
                    return {
                        'color': 'Blue',
                        'backgroundColor': 'white',
                        'fontSize':'{fontSize}'
                    }
                }else{
                    return {
                        'color': 'Gold',
                        'backgroundColor': 'white',
                        'fontSize':'{fontSize}'
                    }
                }
            };

            """.replace("{fontSize}", TABLE_FONTSIZE))
    else:
        cellsytle_jscode = JsCode("""
                function(params) {
                        params.columnApi.autoSizeColumns();
                        if (params.data.hasOwnProperty('status')){
                            if(params.data.status == 'Finished'){
                                return {
                                    'color': 'black',
                                    'backgroundColor': 'green',
                                    'fontSize':'{fontSize}'
                                }
                            }
                        }

                        return {
                            'color': 'black',
                            'backgroundColor': 'white',
                            'fontSize':'{fontSize}'
                            }

                    }
                """.replace("{fontSize}", TABLE_FONTSIZE))
    grid_options = gb.build()
    grid_options['getRowStyle'] = cellsytle_jscode
    if chart_type == "Daily Report":
        return AgGrid(data, gridOptions=grid_options, enable_enterprise_modules=True, fit_columns_on_grid_load=True,
                      allow_unsafe_jscode=True)
    else:
        return AgGrid(data, gridOptions=grid_options, enable_enterprise_modules=True, allow_unsafe_jscode=True)


def login(user, pwd):
    session = requests.session()
    url = "https://secure.nicovideo.jp/secure/login?site=niconico"
    params = {
        "mail": user,
        "password": pwd
    }
    session.post(url, params=params)
    return session


def check_server_login(session, movie_id):
    headers = {
        "X-Frontend-Id": "6",
        "X-Frontend-Version": "0"
    }

    actionTrackId = \
        "".join(random.choice(string.ascii_letters + string.digits) for _ in range(10)) \
        + "_" \
        + str(random.randrange(10 ** (12), 10 ** 13))

    url = "https://www.nicovideo.jp/api/watch/v3/{}?actionTrackId={}" \
        .format(movie_id, actionTrackId)
    res = session.post(url, headers=headers).json()
    return res["data"]["comment"]["nvComment"]


def tokyo_time_to_unix_time(tokyo_date_time_str):
    """
    Convert a Tokyo date and time to Unix time.
    """
    # Create a timezone object for Tokyo
    tokyo_tz = pytz.timezone('Asia/Tokyo')

    # Parse the Tokyo date and time string and add the timezone information
    tokyo_date_time = datetime.strptime(tokyo_date_time_str, '%Y-%m-%d').replace(tzinfo=tokyo_tz)

    # Convert the Tokyo date and time to Unix time
    unix_time = int(tokyo_date_time.timestamp())

    return unix_time


def ms_to_time_string(ms):
    """
    Convert a time in milliseconds to a string representation in hours, minutes, and seconds.
    """
    # Calculate the number of seconds and remaining milliseconds
    seconds, milliseconds = divmod(ms, 1000)

    # Calculate the number of hours, minutes, and seconds
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    # Create the time string
    if hours > 0:
        time_string = f"{hours:02}時{minutes:02}分{seconds:02}秒"
    elif minutes > 0:
        time_string = f"{minutes:02}分{seconds:02}秒"
    else:
        time_string = f"{seconds:02}秒"
    return time_string


def parse_comments(comment):
    """
    {
      "id": "874878644481122398", //コメントID
      "no": 16925, //動画内でのコメント番号
      "vposMs": 682300, //動画内の投稿場所
      "body": "コメントだよ", //投稿内容
      "commands": [ //コマンドのリスト
        "184",
        "device:3DS"
      ],
      "userId": "1MoG8ntWStspL0v-Wg5rdAbbn_4", //ユーザーID
      "isPremium": false, //投稿者がプレミアムかどうか
      "score": 0, //NGスコア
      "postedAt": "2014-11-14T19:51:38+09:00", //投稿された日時
      "nicoruCount": 0, //にこられた数
      "nicoruId": null, //不明
      "source": "leaf", //ソースがどこか
      "isMyPost": false //自分の投稿か
    }
    """
    if "data" not in comment:
        return []
    ids = []
    vposMs = []
    times = []
    texts = []
    scores = []
    postedAt = []
    nicoruCounts = []

    for ele in comment["data"]["threads"]:
        for info in ele["comments"]:
            ids += [info["id"]]
            times += [ms_to_time_string(info["vposMs"])]
            vposMs += [info["vposMs"]]
            texts += [info["body"]]
            scores += [info["score"]]
            postedAt += [info["postedAt"]]
            nicoruCounts += [info["nicoruCount"]]
    return pd.DataFrame.from_dict(
        {"id": ids, "text": texts, "vposMs": vposMs, "time": times, "score": scores, "postedAt": postedAt,
         "nicoruCount": nicoruCounts})


def get_post_comment(session, comment, date, thkey):
    headers = {
        "X-Frontend-Id": "6",
        "X-Frontend-Version": "0",
        "Content-Type": "application/json"
    }

    params = {
        "params": comment["params"],
        "additionals": {
            "when": tokyo_time_to_unix_time(date),
        },
        "threadKey": thkey
    }
    url = comment["server"] + "/v1/threads"
    res = session.post(url, json.dumps(params), headers=headers).json()
    return parse_comments(res)


def get_comments(username, password, movie_id, date):
    session = login(username, password)
    nvComment = check_server_login(session, movie_id)
    return get_post_comment(session, nvComment, date, nvComment["threadKey"])


def load_cache():
    try:
        return pd.read_csv(RESULT_FILE, index_col=False, encoding='utf-8-sig')
    except:
        return None


def show_fig(data, x_col, y_col, time_slot, filter_con):
    fig, ax = plt.subplots(figsize=(15, 10))
    sns.lineplot(data=data,
                 x=x_col,
                 y=y_col,
                 marker='o',
                 sort=False,
                 ax=ax)
    y = data[data[x_col] == time_slot][y_col].max()
    text = data[data[x_col] == time_slot]["text"].max()
    ax.set_xlabel(x_col, fontweight='bold', fontsize=30, color="red", loc="center")
    ax.set_ylabel(y_col, fontweight='bold', fontsize=30, color="red")
    plt.gcf().autofmt_xdate(rotation=90)
    plt.xticks(data[x_col][::2])
    plt.axhline(y=filter_con, color='red', linestyle='--')
    plt.text(time_slot, y, text, color='red')
    legend = plt.legend(frameon=True,
                        edgecolor='black',
                        framealpha=0.2,
                        fontsize=10,
                        handlelength=1,
                        handletextpad=0.2,
                        labelspacing=0.1,
                        borderpad=0.1,
                        loc='upper right')

    legend.get_frame().set_linewidth(0.1)
    st.pyplot(fig)


def show_figs(data_show, indicator, time_slot, filter_con):
    st.markdown("## Comment %sの変化図" % indicator)
    show_fig(data_show, "time", indicator, time_slot, filter_con)


def on_scraping(username, password, movie_id, start_date, end_date, check_date, res_list):
    if password is None or len(password) == 0:
        st.error("Passwordを入力してくだい。")
        return
    save_user_pw(username, password)
    cur = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    dates = []
    while cur <= end:
        cur = cur + timedelta(days=1)
        dates += [cur.strftime('%Y-%m-%d')]

    progress_bar = st.progress(0)
    max_len = len(dates)
    for i, cur_date in enumerate(dates):
        tmp = get_comments(username, password, movie_id, cur_date)
        if tmp is not None:
            tmp["movie id"] = movie_id
            res_list += [tmp]
            progress_bar.progress(i * 100 // max_len)
        time.sleep(1.2)
    result = pd.concat(res_list).drop_duplicates()
    result["check date"] = check_date
    result.to_csv(RESULT_FILE, index=False)
    progress_bar.empty()


def on_reverse():
    if "index" in st.session_state and st.session_state["index"] > 0:
        st.session_state["index"] -= 1
    else:
        st.session_state["index"] = 0


def on_forward(max_len):
    if "index" in st.session_state and st.session_state["index"] < max_len - 1:
        st.session_state["index"] += 1
    else:
        st.session_state["index"] = 0


def show_playbar(data, col, con):
    index = 0
    if "index" in st.session_state:
        index = st.session_state["index"]
    data = data[data[col] >= con]
    st.markdown("### Play comments")
    reverse_btn, time_select, forward_btn = st.columns([1, 12, 1])
    times = ["0"] + data["time"].tolist()
    time_plot = time_select.select_slider(
        '',
        options=times,
        value=times[index + 1]
    )
    reverse_btn.button('⏪',
                       on_click=on_reverse,
                       args=())
    forward_btn.button('⏩',
                       on_click=on_forward,
                       args=(len(times),))
    return time_plot


def reformat_comments(texts):
    res = []
    i = 1
    for text in texts:
        res += ["%dth: %s" % (i, text)]
        i += 1
    return "\n".join(res)


def load_user_pw():
    if not os.path.exists(USER_INFO_FILE):
        return "", ""
    with open(USER_INFO_FILE, 'r') as f:
        read_contents = f.readlines()
    if len(read_contents) != 2:
        return "", ""
    else:
        return read_contents[0], read_contents[1]


def save_user_pw(user, pw):
    info = "%s\n%s" % (user, pw)
    with open(USER_INFO_FILE, 'w') as f:
        f.writelines(info)


if __name__ == "__main__":
    set_up_page()
    default_user, password = load_user_pw()
    username_input,password_input = st.columns(2)
    username = username_input.text_input("Niconico Username", default_user, key="username", )
    password = password_input.text_input("Password", password, type='password', key="password")
    startdate_input_title, enddate_input_title, movie_id_title = st.columns(3)
    start_date_input, end_date_input, movie_id_input = st.columns(3)
    startdate_input_title.markdown("#### Start日付")
    enddate_input_title.markdown("#### Endの日付")
    movie_id_title.markdown("#### Video ID")
    start_date = start_date_input.date_input(
        "",
        datetime.now(),
        key="start")

    end_date = end_date_input.date_input(
        "",
        datetime.now(),
        key="end")
    check_date = datetime.now()
    start_date = start_date.strftime('%Y-%m-%d')
    end_date = end_date.strftime('%Y-%m-%d')
    movie_id = movie_id_input.text_input('', 'so41866051')
    data = load_cache()
    result = None
    res_list = []
    if len(movie_id) > 0:
        if data is not None:
            result = data[(data["check date"] == check_date) & (data["movie id"] == movie_id)]
            # result = data
            if len(result) == 0:
                result = None
            res_list += [data]
        st.button('Search',
                  on_click=on_scraping,
                  args=(username,
                        password,
                        movie_id,
                        start_date,
                        end_date,
                        check_date,
                        res_list))
        if data is not None and len(data) > 0:
            data["count"] = 1
            data = data.groupby(['time', 'text']).agg(
                {'count': 'count', "score": "mean", 'nicoruCount': 'sum'}).reset_index()
            data_show = data.copy()
            data_show = data_show.groupby('time').agg(
                {'count': 'sum', "score": "mean", "text": reformat_comments, 'nicoruCount': 'sum'}).reset_index()
            data_show = data_show.astype({'count': 'int32', 'nicoruCount': 'int32'})
            filter_con_select, indicator_select = st.columns(2)
            indicator = indicator_select.selectbox('Select indicator', ["count", "nicoruCount"])
            max_num = max(data_show[indicator].max(), 0)
            filter_con = filter_con_select.number_input('Select lower limit %s' % indicator, min_value=0,
                                                        max_value=max_num,
                                                        value=(min(max_num, 30)))
            time_slot = show_playbar(data_show, indicator, filter_con)
            show_figs(data_show, indicator, time_slot, filter_con)
            create_table(data[SHOW_COLS], "")
            st.download_button(label="Download Comment",
                               data=data.to_csv().encode('utf-8'),
                               file_name='nico_nico_%s.csv' % movie_id,
                               mime='text/csv')

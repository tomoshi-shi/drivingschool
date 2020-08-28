#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import random
import time
import datetime
import slackweb
import json

LOGIN_ACTION = 'https://www.e-license.jp/el2/pc/p01a.action'
RESERVATION_ACTION = 'https://www.e-license.jp/el2/pc/p03a.action'
LOGOUT_ACTION = 'https://www.e-license.jp/el2/pc/logout.action?b.schoolCd=mEuWeEoosDo%2BbrGQYS%2B1OA%3D%3D'
TIMEOUT = 10
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36"}


def main():
    # メンテナンス中であるかチェック
    is_under_maintenance = False
    is_under_maintenance = check_under_maintenance()

    if(is_under_maintenance == True):
        notify_in_maintenance()
    else:
        soups = []
        # ログイン処理を実施し、各ページの結果を抽出
        soups = login()
        # 予約可能な日付と時刻を通知
        notify_not_in_maintenance(soups)
        # ログアウト処理実行
        logout()


def lambda_handler(event, context):
    main()

    return {
        'statusCode': 200
    }


def check_under_maintenance():
    url = 'https://www.e-license.jp/el2/?abc=mEuWeEoosDo%2BbrGQYS%2B1OA%3D%3D'
    keyword = '只今、システムメンテナンス中です。'

    # セッションを開始
    session = requests.session()

    # スクレイピング実行
    res = session.get(url, timeout = TIMEOUT, headers = HEADERS)
    res.encoding = 'shift_jis'
    soup = BeautifulSoup(res.text, 'html.parser')

    if(soup.text in keyword == True):
        return True
    else:
        return False


def login():
    soups = []
    pages = [1, 2]

    # セッションを開始
    session = requests.session()

    # ログイン実行前にスリープする
    sleep_time = random.uniform(3.5, 7.0)
    time.sleep(sleep_time)

    # INパラメータ設定
    inparam = {
         "b.studentId": os.environ['login_id'],
         "b.password": os.environ['login_password'],
         "method:doLogin": '%83%8D%83O%83C%83%93',
         "b.wordsStudentNo": ' %8B%B3%8FK%90%B6%94%D4%8D%86',
         "b.processCd": '',
         "b.kamokuCd": '',
         "b.schoolCd": 'mEuWeEoosDo+brGQYS+1OA==',
         "index": '',
         "server": 'el2'
    }

    # ログイン処理実行
    res = session.post(LOGIN_ACTION, data=inparam, timeout = TIMEOUT, headers = HEADERS)
    res.encoding = 'shift_jis'
    soup = BeautifulSoup(res.text, 'html.parser')

    # エラーの場合例外を発生
    res.raise_for_status() 

    # 1ページ目の結果を格納
    soups.append(soup)

    # セッションを維持したまま2ページ目以降を抽出
    # ページごとに抽出
    for page in pages:
        soups.append(get_reservation_page(session, page))

    return soups


def get_reservation_page(session, page):
    # ログアウト実行前にスリープする
    sleep_time = random.uniform(3.5, 7.5)
    time.sleep(sleep_time)

    # UNIX時刻(日本時間)を13桁で抽出
    now = datetime.datetime.now() + datetime.timedelta(seconds = 33)
    unixtime = int(now.timestamp() * 1000)

    # INパラメータ設定
    inparam = {
        "b.schoolCd": 'mEuWeEoosDo+brGQYS+1OA==',
        "b.processCd": 'N',
        "b.kamokuCd": '0',
        "b.lastScreenCd": '',
        "b.instructorTypeCd": '0',
        "b.dateInformationType": '',
        "b.infoPeriodNumber": '',
        "b.carModelCd": '1302',
        "b.instructorCd": '0',
        "b.page": str(page),
        "b.groupCd": '1',
        "b.changeInstructorFlg": '0',
        "b.nominationInstructorCd": '0',
        "upDate": str(unixtime)
    }

    # 抽出処理実行
    res = session.post(RESERVATION_ACTION, data=inparam, timeout = TIMEOUT, headers = HEADERS)
    res.encoding = 'shift_jis'
    soup = BeautifulSoup(res.text, 'html.parser')

    # エラーの場合例外を発生
    res.raise_for_status() 

    return soup


def notify_in_maintenance():
    message = ""

    # 通知する文言を設定
    message = message + "メンテナンス中\n"

    # slackへ通知
    slack = slackweb.Slack(url = os.environ['slack_url'])
    slack.notify(text = message)


def notify_not_in_maintenance(soups):
    reservations = []
    vacants = []
    message = ""

    for soup in soups:
        hours = []

        # 抽出対象のTABLEを抽出
        table = soup.html.select("table.set")[1]

        # 日付を取得
        tds = table.select("tr.carender td")
        for td in tds:
            if td.text == "":
                continue
            else:
                hour = td.text.split()[0][-5:]
                hours.append(hour)

        # 予約表を抽出
        trs = table.select("tr.date")
        for tr in trs:
            tds = tr.select("td")
            i = 1
            day = tds[0].text.split()[0] + tds[0].text.split()[1]
            for td in tds[1:len(hours)+1]:
                status = td["class"][0]
                if status == "status0" or status == "status9":
                    # 予約済み・空きあり以外
                    i = i + 1
                    continue
                elif status == "status3":
                    # 予約済み
                    reservations.append([day, hours[i -1]])
                elif status == "status1":
                    # 空きあり
                    vacants.append([day, hours[i -1]])
                i = i + 1

    # 通知する文言を設定
    if len(vacants) == 0:
        # 予約可能枠がない場合メンションをつけない
        message = message + "予約可能枠\n"
        message = message + "空きなし\n"
    else:
        message = message + "<!channel>\n\n"
        message = message + "予約可能枠\n"
        for vacant in vacants:
            message = message + vacant[0] + " " + vacant[1] + "\n"

    message = message + "\n"

    message = message + "予約済み枠\n"
    if len(reservations) == 0:
        message = message + "予約なし\n"
    else:
        for reservation in reservations:
            message = message + reservation[0] + " " + reservation[1] + "\n"

    # slackへ通知
    slack = slackweb.Slack(url = os.environ['slack_url'])
    slack.notify(text = message)


def logout():
    # セッションを開始
    session = requests.session()

    # ログアウト実行前にスリープする
    sleep_time = random.uniform(3.5, 7.0)
    time.sleep(sleep_time)

    # ログアウト処理実行
    res = session.get(LOGOUT_ACTION, timeout = TIMEOUT, headers = HEADERS)
    res.encoding = 'shift_jis'
    soup = BeautifulSoup(res.text,  'html.parser')


    # エラーの場合例外を発生
    res.raise_for_status() 

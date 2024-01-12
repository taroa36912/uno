import argparse
import os
import math
import random
import sys
import socketio
import time

from rich import print



"""
定数
"""
# Socket通信の全イベント名
class SocketConst:
    class EMIT:
        JOIN_ROOM = 'join-room' # 試合参加
        RECEIVER_CARD = 'receiver-card' # カードの配布
        FIRST_PLAYER = 'first-player' # 対戦開始
        COLOR_OF_WILD = 'color-of-wild' # 場札の色を変更する
        UPDATE_COLOR = 'update-color' # 場札の色が変更された
        SHUFFLE_WILD = 'shuffle-wild' # シャッフルしたカードの配布
        NEXT_PLAYER = 'next-player' # 自分の手番
        PLAY_CARD = 'play-card' # カードを出す
        DRAW_CARD = 'draw-card' # カードを山札から引く
        PLAY_DRAW_CARD = 'play-draw-card' # 山札から引いたカードを出す
        CHALLENGE = 'challenge' # チャレンジ
        PUBLIC_CARD = 'public-card' # 手札の公開
        POINTED_NOT_SAY_UNO = 'pointed-not-say-uno' # UNO宣言漏れの指摘
        SPECIAL_LOGIC = 'special-logic' # スペシャルロジック
        FINISH_TURN = 'finish-turn' # 対戦終了
        FINISH_GAME = 'finish-game' # 試合終了
        PENALTY = 'penalty' # ペナルティ


# UNOのカードの色
class Color:
    RED = 'red' # 赤
    YELLOW = 'yellow' # 黄
    GREEN = 'green' # 緑
    BLUE = 'blue' # 青
    BLACK = 'black' # 黒
    WHITE = 'white' # 白


# UNOの記号カード種類
class Special:
    SKIP = 'skip' # スキップ
    REVERSE = 'reverse' # リバース
    DRAW_2 = 'draw_2' # ドロー2
    WILD = 'wild' # ワイルド
    WILD_DRAW_4 = 'wild_draw_4' # ワイルドドロー4
    WILD_SHUFFLE = 'wild_shuffle' # シャッフルワイルド
    WHITE_WILD = 'white_wild' # 白いワイルド


# カードを引く理由
class DrawReason:
    DRAW_2 = 'draw_2' # 直前のプレイヤーがドロー2を出した場合
    WILD_DRAW_4 = 'wild_draw_4' # 直前のプレイヤーがワイルドドロー4を出した場合
    BIND_2 = 'bind_2' # 直前のプレイヤーが白いワイルド（バインド2）を出した場合
    SKIP_BIND_2 = 'skip_bind_2' # 直前のプレイヤーが白いワイルド（スキップバインド2）を出した場合
    NOTHING = 'nothing' # 理由なし


TEST_TOOL_HOST_PORT = '3000' # 開発ガイドラインツールのポート番号
ARR_COLOR = [Color.RED, Color.YELLOW, Color.GREEN, Color.BLUE] # 色変更の選択肢


"""
コマンドラインから受け取った変数等
"""
parser = argparse.ArgumentParser(description='A demo player written in Python')
parser.add_argument('host', action='store', type=str, help='Host to connect')
parser.add_argument('room_name', action='store', type=str, help='Name of the room to join')
parser.add_argument('player', action='store', type=str, help='Player name you join the game as')
parser.add_argument('event_name', action='store', nargs='?', default=None, type=str, help='Event name for test tool') # 追加


args = parser.parse_args(sys.argv[1:])
host = args.host # 接続先（ディーラープログラム or 開発ガイドラインツール）
room_name = args.room_name # ディーラー名
player = args.player # プレイヤー名
event_name = args.event_name # Socket通信イベント名
is_test_tool = TEST_TOOL_HOST_PORT in host # 接続先が開発ガイドラインツールであるかを判定
SPECIAL_LOGIC_TITLE = '◯◯◯◯◯◯◯◯◯◯◯◯◯◯◯◯◯◯◯◯◯' # スペシャルロジック名
TIME_DELAY = 10 # 処理停止時間


once_connected = False
id_e = [0]*4 #敵のidを保存する
id = 'welldefined' # 自分のID
uno_declared = {} # 他のプレイヤーのUNO宣言状況
player_challenge = [[0]*4] #他プレイヤーのチャレンジ回数を記録
player_challenge_succeed = [[0]*4] #他プレイヤーのチャレンジ成功回数を記録
cards_colors = [] # 対戦開始時のカードがワイルドだった時, シャッフルワイルドが場札に出された時専用
cards_all = [[0]]*5 # 0~3にプレイヤー(順番)、4に場札の捨て札を記録する
my_turn = 0 # 自分の順番の数を代入する
flag = 0 # selectで使うフラグ変数


"""
コマンドライン引数のチェック
"""
if not host:
    # 接続先のhostが指定されていない場合はプロセスを終了する
    print('Host missed')
    os._exit(0)
else:
    print('Host: {}'.format(host))

# ディーラー名とプレイヤー名の指定があることをチェックする
if not room_name or not player:
    print('Arguments invalid')

    if not is_test_tool:
        # 接続先がディーラープログラムの場合はプロセスを終了する
        os._exit(0)
else:
    print('Dealer: {}, Player: {}'.format(room_name, player))


# 開発ガイドラインツールSTEP1で送信するサンプルデータ
TEST_TOOL_EVENT_DATA = {
    SocketConst.EMIT.JOIN_ROOM: {
        'player': player,
        'room_name': room_name,
    },
    SocketConst.EMIT.COLOR_OF_WILD: {
        'color_of_wild': 'red',
    },
    SocketConst.EMIT.PLAY_CARD: {
        'card_play': { 'color': 'black', 'special': 'wild' },
        'yell_uno': False,
        'color_of_wild': 'blue',
    },
    SocketConst.EMIT.DRAW_CARD: {},
    SocketConst.EMIT.PLAY_DRAW_CARD: {
        'is_play_card': True,
        'yell_uno': True,
        'color_of_wild': 'blue',
    },
    SocketConst.EMIT.CHALLENGE: {
        'is_challenge': True,
    },
    SocketConst.EMIT.POINTED_NOT_SAY_UNO: {
        'target': 'Player 1',
    },
    SocketConst.EMIT.SPECIAL_LOGIC: {
        'title': SPECIAL_LOGIC_TITLE,
    },
}


# Socketクライアント
sio = socketio.Client()



"""
idの整合性を確かめる関数
"""

def id_checker(player):
    global id_e
    if player == id_e[0]:
        return 0
    if player == id_e[1]:
        return 1
    if player == id_e[2]:
        return 2
    if player == id_e[3]:
        return 3
    
    return 4


"""
出すカードを選出する

Args:
    cards (list): 自分の手札
    before_caard (*): 場札のカード
"""
def select_play_card(cards, before_caard, number_card_of_player):
    global flag
    cards_wild = [] # 白いワイルドを格納
    cards_wild_shuffle = [] # シャッフルワイルドを格納
    cards_wild_white = [] # 白いワイルドを格納
    cards_wild4 = [] # ワイルドドロー4を格納
    cards_color = [] # 同じ色のカードを格納
    cards_number = [] # 同じ数字のカードを格納
    cards_reverse = [] #　revreseを格納
    cards_skip = [] # skipを格納
    cards_draw_2 = [] # draw_2を格納
    list = [] # 出せるカードを優先順位順に格納
    flag = 0 # 最終的に決めるフラグ変数
    flag_1 = 1 # シャッフルワイルドについてのフラグ変数
    flag_2 = 1 # フラグ第２変数 二つとも1のときのみシャッフルを適用
    flag_3 = 1 # フラグ第３変数　これは独立
    count = 0 # ワイルドの手札の枚数をカウントする
    number_of_my_card = 0 # 自分の手札の枚数をカウントする
    
    # 場札と照らし合わせ出せるカードを抽出する
    for card in cards:
        card_special = card.get('special')
        card_number = card.get('number')
        if str(card_special) == Special.WILD_DRAW_4: # 手札にドロー4がある場合、抽出
            cards_wild4.append(card)
            count += 1
        elif (str(card_special) == Special.WILD): # 手札にワイルドがある場合、抽出
            cards_wild.append(card)
            count += 1
        elif (str(card_special) == Special.WILD_SHUFFLE): # 手札にシャッフルがある場合、抽出
            cards_wild_shuffle.append(card)
            count += 1
        elif (str(card_special) == Special.WHITE_WILD): # 手札に白ワイルドがある場合、抽出
            cards_wild_white.append(card)
            count += 1
        elif (
            (str(card_special) == Special.DRAW_2) and 
              ((str(card.get('color')) == str(before_caard.get('color'))) or (str(card_special) == str(before_caard.get('special'))))
              ): # 手札に出せるドロー２がある場合、抽出
            cards_draw_2.append(card)
        elif (
            (str(card_special) == Special.SKIP) and 
              ((str(card.get('color')) == str(before_caard.get('color'))) or (str(card_special) == str(before_caard.get('special'))))
              ): # 手札に出せるスキップがある場合、抽出
            cards_skip.append(card)
        elif (
            (str(card_special) == Special.REVERSE) and
            ((str(card.get('color')) == str(before_caard.get('color'))) or (str(card_special) == str(before_caard.get('special'))))
            ): # 手札に出せるリバースがある場合、抽出
            cards_reverse.append(card)
        elif (str(card.get('color')) == str(before_caard.get('color'))): 
            # 場札と同じ色のカード
            cards_color.append(card)
        elif (
            (card_special and str(card_special) == str(before_caard.get('special'))) or
            ((card_number is not None or (card_number is not None and int(card_number) == 0)) and
             (before_caard.get('number') and int(card_number) == int(before_caard.get('number'))))
        ):
            # 場札と数字が同じカード
            cards_number.append(card)
        elif (str(card_special) == Special.SKIP or str(card_special) == Special.DRAW_2):
            flag_2 = 0

    """
    以下、シャッフルワイルドを出すアルゴリズムについてのプログラムである
    """
    if(len(cards_wild_shuffle) > 0):
        if(number_of_my_card == 1):
            list = cards_wild_shuffle
            if len(list) > 0:
                return list[0]
            else:
                return None
        player_card_sum = 0
        for k, v in number_card_of_player.items():
            if k == id:
                number_of_my_card = v
            elif v < 3:
                flag_3 = 1
            player_card_sum += v
        if ((number_of_my_card < player_card_sum // 4)):
            flag_1 = 0
            
    if(flag_1 and flag_2) or flag_3:
        flag = 1
    else:
        flag = 0
        
    """
    ここまで
    """
    
    cards_color_ = sorted(cards_color, key=lambda x: int(x["number"]), reverse=True)

    
    if(count > 1):
        if(flag):
            list = cards_wild_shuffle + cards_wild + cards_wild4 + cards_wild_white + cards_draw_2 + cards_skip + cards_reverse + cards_color_ + cards_number
        else:
            list = cards_wild + cards_wild4 + cards_wild_white + cards_draw_2 + cards_skip + cards_reverse + cards_color_ + cards_number
        
        if len(list) > 0:
            return list[0]
        else:
            return None
    
    
    """
    if(count == 1 && ):
        if(flag):
            list = cards_wild_shuffle + cards_draw_2 + cards_skip + cards_reverse + cards_color + cards_number
        else:
            list = cards_draw_2 + cards_skip + cards_reverse + cards_color + cards_number
        
        if len(list) > 0:
            return list[0]
        else:
            return None
    """

    if(len(cards_color_) > 0):
        card_number = cards_color_[0].get('number')
        if(flag):
            if (card_number and before_caard.get('number') and int(card_number) < int(before_caard.get('number'))):
                list = cards_wild_shuffle + cards_draw_2 + cards_skip + cards_reverse + cards_number + cards_color_
            else:
                list = cards_wild_shuffle + cards_draw_2 + cards_skip + cards_reverse + cards_color_ + cards_number
        else:
            if (card_number and before_caard.get('number') and int(card_number) < int(before_caard.get('number'))):
                list = cards_wild_white + cards_draw_2 + cards_skip + cards_reverse + cards_number + cards_color_
            else:
                list = cards_wild_white + cards_draw_2 + cards_skip + cards_reverse + cards_color_ + cards_number
        
        if len(list) > 0:
            return list[0]
        else:
            return None
        
        
            
    if(flag):
        list = cards_wild_shuffle + cards_wild_white + cards_draw_2 + cards_skip + cards_reverse + cards_color_ + cards_number 
    else:
        list = cards_wild_white + cards_draw_2 + cards_skip + cards_reverse + cards_color_ + cards_number
        

        
    if len(list) > 0:
        return list[0]
    else:
        return None

"""
乱数取得

Args:
    num (int):

Returns:
    int:
"""
def random_by_number(num):
    return math.floor(random.random() * num)


"""
変更する色を選出する

Returns:
    str:
"""

def select_change_color_r():
    return ARR_COLOR[random_by_number(len(ARR_COLOR))]


def select_change_color(cards):
    # 自分の手札に一番多い色を選択する
    if(len(cards) > 0):
        color_number = [0,0,0,0]
        color_special = [0,0,0,0]
        for card in cards:
            if(card.get('color') == Color.RED):
                if(card.get('special')):
                    color_number[0] += 20
                    color_special[0] += 1
                elif(card.get('number')):
                    color_number[0] += int(card.get('number'))
                else:
                    color_number[0] += 1
            elif(card.get('color') == Color.YELLOW):
                if(card.get('special')):
                    color_number[1] += 20
                    color_special[1] += 1
                elif(card.get('number')):
                    color_number[1] += int(card.get('number'))
                else:
                    color_number[1] += 1
            elif(card.get('color') == Color.GREEN):
                if(card.get('special')):
                    color_number[2] += 20
                    color_special[2] += 1
                elif(card.get('number')):
                    color_number[2] += int(card.get('number'))
                else:
                    color_number[2] += 1
            elif(card.get('color') == Color.BLUE):
                if(card.get('special')):
                    color_number[3] += 20
                    color_special[3] += 1
                elif(card.get('number')):
                    color_number[3] += int(card.get('number'))
                else:
                    color_number[3] += 1
                
        max_value = max(color_number)
        max_indexes = [index for index, value in enumerate(color_number) if value == max_value]
        # color_specialの中で最も中身の整数が大きいインデックスを抽出
        i = max(max_indexes, key=lambda x: color_special[x])
            
        return ARR_COLOR[i]
    
    return ARR_COLOR[random_by_number(len(ARR_COLOR))]

"""
チャンレンジするかを決定する

Returns:
    bool:
"""
def is_challenge(number_card_of_player, cards):
    for k, v in number_card_of_player.items():
        if k == id:
            if v == 1:
                return True
            
    if(shuffle_check(cards)):
        return True
    
        
    return False

"""
他のプレイヤーのUNO宣言漏れをチェックする

Args:
    number_card_of_player (Any):
"""
def determine_if_execute_pointed_not_say_uno(number_card_of_player):
    global id, uno_declared

    target = None
    # 手札の枚数が1枚だけのプレイヤーを抽出する
    # 2枚以上所持しているプレイヤーはUNO宣言の状態をリセットする
    for k, v in number_card_of_player.items():
        if k == id:
            # 自分のIDは処理しない
            break
        elif v == 1:
            # 1枚だけ所持しているプレイヤー
            target = k
            # 抽出したプレイヤーがUNO宣言を行っていない場合宣言漏れを指摘する
            if (target not in uno_declared.keys()):
                send_event(SocketConst.EMIT.POINTED_NOT_SAY_UNO, { 'target': target })
                time.sleep(TIME_DELAY / 1000)
            break
        elif k in uno_declared:
            # 2枚以上所持しているプレイヤーはUNO宣言の状態をリセットする
            del uno_declared[k]

    if target == None:
        # 1枚だけ所持しているプレイヤーがいない場合、処理を中断する
        return

    # 抽出したプレイヤーがUNO宣言を行っていない場合宣言漏れを指摘する
    #if (target not in uno_declared.keys()):
    #    send_event(SocketConst.EMIT.POINTED_NOT_SAY_UNO, { 'target': target })
    #    time.sleep(TIME_DELAY / 1000)
    
    
"""
自分の手札にシャッフルが入っているかどうか確認する
"""

def shuffle_check(cards):
    for card in cards:
        card_special = card.get('special')
        if(str(card_special) == Special.WILD_SHUFFLE):
            return True
        
    return False
            
    
    


"""
各プレイヤーのチャレンジ回数並びに成功回数を記録する
"""

def challenge_recorded():
    print()


"""
個別コールバックを指定しないときの代替関数
"""
def pass_func(err):
    return


"""
送信イベント共通処理

Args:
    event (str): Socket通信イベント名
    data (Any): 送信するデータ
    callback (func): 個別処理
"""
def send_event(event, data, callback = pass_func):
    print('Send {} event.'.format(event))
    print('req_data: ', data)

    def after_func(err, res):
        if err:
            print('{} event failed!'.format(event))
            print(err)
            return

        print('Send {} event.'.format(event))
        print('res_data: ', res)
        callback(res)

    sio.emit(event, data, callback=after_func)


"""
受信イベント共通処理

Args:
    event (str): Socket通信イベント名
    data (Any): 送信するデータ
    callback (func): 個別処理
"""
def receive_event(event, data, callback = pass_func):
    print('Receive {} event.'.format(event))
    print('res_data: ', data)

    callback(data)


"""
Socket通信の確立
"""
@sio.on('connect')
def on_connect():
    print('Client connect successfully!')

    if not once_connected:
        if is_test_tool:
            # テストツールに接続
            if not event_name:
                # イベント名の指定がない（開発ガイドラインSTEP2の受信のテストを行う時）
                print('Not found event name')
            elif not event_name in TEST_TOOL_EVENT_DATA:
                # イベント名の指定があり、テストデータが定義されていない場合はエラー
                print('Undefined test data. eventName: ', event_name)
            else:
                # イベント名の指定があり、テストデータが定義されている場合は送信する(開発ガイドラインSTEP1の送信のテストを行う時)
                send_event(event_name, TEST_TOOL_EVENT_DATA[event_name])
        else:
            # ディーラープログラムに接続
            data = {
                'room_name': room_name,
                'player': player,
            }

            def join_room_callback(*args):
                global once_connected, id
                print('Client join room successfully!')
                once_connected = True
                id = args[0].get('your_id')
                print('My id is {}'.format(id))

            send_event(SocketConst.EMIT.JOIN_ROOM, data, join_room_callback)


"""
Socket通信を切断
"""
@sio.on('disconnect')
def on_disconnect():
    print('Client disconnect.')
    os._exit(0)


"""
Socket通信受信
"""
# プレイヤーがゲームに参加
@sio.on(SocketConst.EMIT.JOIN_ROOM)
def on_join_room(data_res):
    receive_event(SocketConst.EMIT.JOIN_ROOM, data_res)


# カードが手札に追加された
@sio.on(SocketConst.EMIT.RECEIVER_CARD)
def on_reciever_card(data_res):
    global cards_colors
    if(len(data_res.get('cards_receive')) == 7):
        cards_colors = data_res.get('cards_receive')
    receive_event(SocketConst.EMIT.RECEIVER_CARD, data_res)


# 対戦の開始
@sio.on(SocketConst.EMIT.FIRST_PLAYER)
def on_first_player(data_res):
    global id_e, my_turn
    ids = data_res.get('play_order')
    i = 0
    for id_ in ids:
        id_e[i] = id_
        if id_ == id:
            my_turn = i
        i += 1
    i = 0
    receive_event(SocketConst.EMIT.FIRST_PLAYER, data_res)


# 場札の色指定を要求
@sio.on(SocketConst.EMIT.COLOR_OF_WILD)
def on_color_of_wild(data_res):
    def color_of_wild_callback(data_res):
        global cards_colors
        color = select_change_color(cards_colors)
        data = {
            'color_of_wild': color,
        }

        # 色変更を実行する
        send_event(SocketConst.EMIT.COLOR_OF_WILD, data)

    receive_event(SocketConst.EMIT.COLOR_OF_WILD, data_res, color_of_wild_callback)


# 場札の色が変わった
@sio.on(SocketConst.EMIT.UPDATE_COLOR)
def on_update_color(data_res):
    receive_event(SocketConst.EMIT.UPDATE_COLOR, data_res)


# シャッフルワイルドにより手札状況が変更
@sio.on(SocketConst.EMIT.SHUFFLE_WILD)
def on_shuffle_wild(data_res):
    def shuffle_wild_calback(data_res):
        global cards_colors
        cards_colors = data_res.get('cards_receive')
        global uno_declared
        uno_declared = {}
        for k, v in data_res.get('number_card_of_player').items():
            if v == 1:
                # シャッフル後に1枚になったプレイヤーはUNO宣言を行ったこととする
                uno_declared[data_res.get('player')] = True
                break
            elif k in uno_declared:
                # シャッフル後に2枚以上のカードが配られたプレイヤーはUNO宣言の状態をリセットする
                if data_res.get('player') in uno_declared:
                    del uno_declared[k]

    receive_event(SocketConst.EMIT.SHUFFLE_WILD, data_res, shuffle_wild_calback)


# 自分の番
@sio.on(SocketConst.EMIT.NEXT_PLAYER)
def on_next_player(data_res):
    def next_player_calback(data_res):
        cards = data_res.get('card_of_player')
        number_cards = data_res.get('number_card_of_player')
        determine_if_execute_pointed_not_say_uno(number_cards)

        if (data_res.get('draw_reason') == DrawReason.WILD_DRAW_4):
            # カードを引く理由がワイルドドロー4の時、チャレンジを行うことができる。
            if is_challenge(number_cards, cards):
                send_event(SocketConst.EMIT.CHALLENGE, { 'is_challenge': True} )
                return

        if str(data_res.get('must_call_draw_card')) == 'True':
            # カードを引かないと行けない時
            send_event(SocketConst.EMIT.DRAW_CARD, {})
            return

        #  スペシャルロジックを発動させる
        special_logic_num_random = random_by_number(10)
        if special_logic_num_random == 0:
            send_event(SocketConst.EMIT.SPECIAL_LOGIC, { 'title': SPECIAL_LOGIC_TITLE })

        # フラグ変数のリセット    
        global flag
        flag = 0
        play_card = select_play_card(cards, data_res.get('card_before'), number_cards)

        if play_card:
            # 選出したカードがある時
            print('selected card: {} {}'.format(play_card.get('color'), play_card.get('number') or play_card.get('special')))
            data = {
                'card_play': play_card,
                'yell_uno': len(cards) == 2, # 残り手札数を考慮してUNOコールを宣言する
            }

            if play_card.get('special') == Special.WILD or play_card.get('special') == Special.WILD_DRAW_4:
                color = select_change_color(cards)
                data['color_of_wild'] = color

            # カードを出すイベントを実行
            send_event(SocketConst.EMIT.PLAY_CARD, data)
        else:
            # 選出したカードが無かった時

            # draw-cardイベント受信時の個別処理
            def draw_card_callback(res):
                if not res.get('can_play_draw_card'):
                    # 引いたカードが場に出せないので処理を終了
                    return

                # 以後、引いたカードが場に出せるときの処理
                play_card = res.get('draw_card')
                special = play_card[0].get('special')
                
                if ((not special) or (special and (str(special) is not Special.WILD_SHUFFLE)) or (flag)):
                    data = {
                        'is_play_card': True,
                        'yell_uno': len(cards + play_card) == 2, # 残り手札数を考慮してUNOコールを宣言する
                    }                              
                else:
                    data = {
                        'is_play_card': False,
                        'yell_uno': len(cards + play_card) == 1, # 残り手札数を考慮してUNOコールを宣言する
                    }
                    
                play_card = play_card[0]               
                if play_card.get('special') == Special.WILD or play_card.get('special') == Special.WILD_DRAW_4:
                    color = select_change_color(cards)
                    data['color_of_wild'] = color

                # 引いたカードを出すイベントを実行
                send_event(SocketConst.EMIT.PLAY_DRAW_CARD, data)

            # カードを引くイベントを実行
            send_event(SocketConst.EMIT.DRAW_CARD, {}, draw_card_callback)

    receive_event(SocketConst.EMIT.NEXT_PLAYER, data_res, next_player_calback)


# カードが場に出た
@sio.on(SocketConst.EMIT.PLAY_CARD)
def on_play_card(data_res):
    def play_card_callback(data_res):
        global cards_all
        player = data_res.get('player')
        cards_all[id_checker(player)].append(data_res.get('card_play'))
        global uno_declared
        # UNO宣言を行った場合は記録する
        if data_res.get('yell_uno'):
            uno_declared[data_res.get('player')] = data_res.get('yell_uno')
        cards_all[4].append(data_res.get('card_play'))

    receive_event(SocketConst.EMIT.PLAY_CARD, data_res, play_card_callback)


# 山札からカードを引いた
@sio.on(SocketConst.EMIT.DRAW_CARD)
def on_draw_card(data_res):
    def draw_card_callback(data_res):
        global uno_declared
        # カードが増えているのでUNO宣言の状態をリセットする
        if data_res.get('player') in uno_declared:
            del uno_declared[data_res.get('player')]

    receive_event(SocketConst.EMIT.DRAW_CARD, data_res, draw_card_callback)


# 山札から引いたカードが場に出た
@sio.on(SocketConst.EMIT.PLAY_DRAW_CARD)
def on_play_draw_card(data_res):
    def play_draw_card_callback(data_res):
        global cards_all
        if data_res.get('is_play_card'):
            player = data_res.get('player')
            cards_all[id_checker(player)].append(data_res.get('card_play'))
        global uno_declared
        # UNO宣言を行った場合は記録する
        if data_res.get('yell_uno'):
            uno_declared[data_res.get('player')] = data_res.get('yell_uno')
        
        if(data_res.get('is_play_card')):
            cards_all[4].append(data_res.get('card_play'))

    receive_event(SocketConst.EMIT.PLAY_DRAW_CARD, data_res, play_draw_card_callback)


# チャレンジの結果
@sio.on(SocketConst.EMIT.CHALLENGE)
def on_challenge(data_res):
    i = id_checker(data_res.get('challenger'))
    if(data_res.get('is_challenge')):
        player_challenge[i] += 1
    if(data_res.get('is_challenge_success')):
        player_challenge_succeed[i] += 1
    receive_event(SocketConst.EMIT.CHALLENGE, data_res)


# チャレンジによる手札の公開
@sio.on(SocketConst.EMIT.PUBLIC_CARD)
def on_public_card(data_res):
    receive_event(SocketConst.EMIT.PUBLIC_CARD, data_res)


# UNOコールを忘れていることを指摘
@sio.on(SocketConst.EMIT.POINTED_NOT_SAY_UNO)
def on_pointed_not_say_uno(data_res):
    receive_event(SocketConst.EMIT.POINTED_NOT_SAY_UNO, data_res)


# 対戦が終了
@sio.on(SocketConst.EMIT.FINISH_TURN)
def on_finish_turn(data_res):
    def finish_turn__callback(data_res):
        global id_e, uno_declared, player_challenge, player_challenge_succeed, cards_colors, cards_all, my_turn
        id_e = [0]*4
        uno_declared = {}
        player_challenge = [[0]*4]
        player_challenge_succeed = [[0]*4]
        cards_colors = []
        cards_all = [[0]]*5
        my_turn = 0

    receive_event(SocketConst.EMIT.FINISH_TURN, data_res, finish_turn__callback)


# 試合が終了
@sio.on(SocketConst.EMIT.FINISH_GAME)
def on_finish_game(data_res):
    receive_event(SocketConst.EMIT.FINISH_GAME, data_res)


# ペナルティ発生
@sio.on(SocketConst.EMIT.PENALTY)
def on_penalty(data_res):
    def penalty_callback(data_res):
        global uno_declared
        # カードが増えているのでUNO宣言の状態をリセットする
        if data_res.get('player') in uno_declared:
            del uno_declared[data_res.get('player')]

    receive_event(SocketConst.EMIT.PENALTY, data_res, penalty_callback)


def main():
    sio.connect(
        host,
        transports=['websocket'],
    )
    sio.wait()

if __name__ == '__main__':
    main()

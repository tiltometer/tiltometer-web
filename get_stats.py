import psycopg2
import psycopg2.extras
import argparse
from datetime import datetime
from google.cloud import firestore

STATS_COLLECTION = u'stats'
SECRET_KEY = b'_5#y2L"Fsdadfnosa4Q8z\n\xec]/'
db = firestore.Client()


class GameStats(object):
    def __init__(self, start, end):
        self.date = datetime.strptime(start, '%Y/%m/%d %H:%M:%S')
        self.start = start
        self.end = end
        self.players = []
        self._populate()
        self.num_hands = sum([player.cnt_hands_won for player in self.players])

    def _to_doc(self):
        doc = {
            'date': self.date.strftime('%m/%d/%Y'),
            'num_hands': self.num_hands,
            'players': [
                {
                    'player_id': player.id_player,
                    'player_name': player.player_name,
                    'hands_won': player.cnt_hands_won,
                    'num_hands': player.cnt_hands,
                    'vpip': player.cnt_vpip,
                    'pfr': player.cnt_pfr,
                    'pfr_opp': player.cnt_pfr_opp,
                    'cbet_flop': player.cnt_f_cbet,
                    'cbet_flop_opp': player.cnt_f_cbet_opp,
                    'cbet_flop_fold': player.cnt_f_cbet_def_action_fold,
                    'cbet_flop_fold_opp': player.cnt_f_cbet_def_opp,
                    'pf_3bet': player.cnt_p_3bet,
                    'pf_3bet_opp': player.cnt_p_3bet_opp
                    }
                for player in self.players
            ]
        }
        print(doc)
        return doc

    def store(self):
        doc_ref = db.collection(STATS_COLLECTION).document(str(self.date.timestamp()))
        doc = self._to_doc()
        doc_ref.set(doc)

    def _populate(self):
        """
        QUERY TO GET DATA NEEDED FOR STATS
        aliases are already handled no need to merge two players at query time
        start and end should be in form 'Y/m/d H:M:S' e.g. 2020/07/31 00:00:00 for game stats for game that began on 7/31
        """
        q = """
        SELECT (sum((case when(cash_hand_player_statistics.id_hand > 0) then  1 else  0 end))) as "cnt_hands", (sum((case when(cash_hand_player_statistics.flg_won_hand) then  1 else  0 end))) as "cnt_hands_won", (cash_hand_player_statistics.id_player) as "id_player", (sum((case when(cash_hand_player_statistics.flg_vpip) then  1 else  0 end))) as "cnt_vpip", (sum((case when(lookup_actions_p.action = '') then  1 else  0 end))) as "cnt_walks", (sum((case when(cash_hand_player_statistics.cnt_p_raise > 0) then  1 else  0 end))) as "cnt_pfr", (sum((case when( lookup_actions_p.action LIKE '__%' OR (lookup_actions_p.action LIKE '_' AND (cash_hand_player_statistics.amt_before > (cash_limit.amt_bb + cash_hand_player_statistics.amt_ante)) AND (cash_hand_player_statistics.amt_p_raise_facing < (cash_hand_player_statistics.amt_before - (cash_hand_player_statistics.amt_blind + cash_hand_player_statistics.amt_ante))) AND (cash_hand_player_statistics.flg_p_open_opp OR cash_hand_player_statistics.cnt_p_face_limpers > 0 OR cash_hand_player_statistics.flg_p_3bet_opp OR cash_hand_player_statistics.flg_p_4bet_opp) )) then  1 else  0 end))) as "cnt_pfr_opp", (sum((case when(cash_hand_player_statistics.flg_f_cbet) then  1 else  0 end))) as "cnt_f_cbet", (sum((case when(cash_hand_player_statistics.flg_f_cbet_opp) then  1 else  0 end))) as "cnt_f_cbet_opp", (sum((case when(cash_hand_player_statistics.enum_f_cbet_action='F') then  1 else  0 end))) as "cnt_f_cbet_def_action_fold", (sum((case when(cash_hand_player_statistics.flg_f_cbet_def_opp) then  1 else  0 end))) as "cnt_f_cbet_def_opp", (sum((case when(cash_hand_player_statistics.flg_p_3bet) then  1 else  0 end))) as "cnt_p_3bet", (sum((case when(cash_hand_player_statistics.flg_p_3bet_opp) then  1 else  0 end))) as "cnt_p_3bet_opp", (date_part('month',  timezone('UTC',  cash_hand_player_statistics.date_played  + INTERVAL '0 HOURS'))) as "date_played_month", (date_part('year',  timezone('UTC',  cash_hand_player_statistics.date_played  + INTERVAL '0 HOURS'))) as "date_played_year", (sum(cash_hand_player_statistics.amt_won)) as "amt_won", (player.player_name) as "player_name" FROM       cash_hand_player_statistics , lookup_actions lookup_actions_p, cash_limit, player WHERE  (cash_hand_player_statistics.id_player = player.id_player) AND (lookup_actions_p.id_action=cash_hand_player_statistics.id_action_p)  AND (cash_limit.id_limit = cash_hand_player_statistics.id_limit)       AND ((cash_hand_player_statistics.id_gametype = 1)AND (cash_hand_player_statistics.id_gametype<>1 OR (cash_hand_player_statistics.id_gametype=1 AND (cash_hand_player_statistics.id_limit in (SELECT hlrl.id_limit FROM cash_limit hlrl WHERE (hlrl.flg_nlpl=false and (CASE WHEN hlrl.limit_currency='SEK' THEN (hlrl.amt_bb*0.15) ELSE (CASE WHEN hlrl.limit_currency='INR' THEN (hlrl.amt_bb*0.020) ELSE (CASE WHEN hlrl.limit_currency='XSC' THEN 0.0 ELSE (CASE WHEN hlrl.limit_currency='PLY' THEN 0.0 ELSE hlrl.amt_bb END) END) END) END)<=1.01) or (hlrl.flg_nlpl=true and (CASE WHEN hlrl.limit_currency='SEK' THEN (hlrl.amt_bb*0.15) ELSE (CASE WHEN hlrl.limit_currency='INR' THEN (hlrl.amt_bb*0.020) ELSE (CASE WHEN hlrl.limit_currency='XSC' THEN 0.0 ELSE (CASE WHEN hlrl.limit_currency='PLY' THEN 0.0 ELSE hlrl.amt_bb END) END) END) END)<=0.51)))))AND ((((date_trunc('day',  timezone('UTC',  cash_hand_player_statistics.date_played  + INTERVAL '0 HOURS')))>='{0}' AND (date_trunc('day',  timezone('UTC',  cash_hand_player_statistics.date_played  + INTERVAL '0 HOURS')))<='{1}')))AND ((((date_trunc('day',  timezone('UTC',  cash_hand_player_statistics.date_played  + INTERVAL '0 HOURS')))>='{0}' AND (date_trunc('day',  timezone('UTC',  cash_hand_player_statistics.date_played  + INTERVAL '0 HOURS')))<='{1}'))))  GROUP BY (player.player_name),(cash_hand_player_statistics.id_player), (date_part('month',  timezone('UTC',  cash_hand_player_statistics.date_played  + INTERVAL '0 HOURS'))), (date_part('year',  timezone('UTC',  cash_hand_player_statistics.date_played  + INTERVAL '0 HOURS')));
        """.format(self.start, self.end)

        conn = psycopg2.connect("dbname=PT4_2020_07_18_094617 user=pt4")
        cur = conn.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)
        cur.execute(q)
        for row in cur.fetchall():
            print(row)
            self.players.append(row)
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', required=True, dest='start')
    parser.add_argument('-e', required=True, dest='end')
    args = parser.parse_args()

    stats = GameStats(args.start, args.end)
    stats.store()

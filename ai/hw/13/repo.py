import ydb
from _ydb import execute_select_query, execute_update_query
import json

class QuizRepo:
    def __init__(self, pool: ydb.SessionPool):
        self.pool = pool
    
    async def get_question(self):
        query = f"""
            SELECT `question_id`, `quest`
            FROM `questions` 
        """

        results = execute_select_query(self.pool, query)

        if len(results) == 0:
            return []
        if results[0]['quest'] is None:
            return []
        out = []
        for item in results:
            out.append(json.loads(item['quest']))

        return out      

    async def get_quiz_index(self, user_id):        
        query = f"""
            DECLARE $user_id AS Uint64;

            SELECT  question_index
            FROM    quiz_state
            WHERE user_id == $user_id;
        """
        results = execute_select_query(self.pool, query, user_id=user_id)

        if len(results) == 0:
            return 0
        if results[0]["question_index"] is None:
            return 0
        return results[0]["question_index"]   

    async def update_quiz_index(self, user_id, question_index):
        query = f"""
            DECLARE $user_id         AS Uint64;
            DECLARE $question_index  AS Uint64;

            UPSERT INTO quiz_state (user_id, question_index) VALUES ($user_id, $question_index);
        """
        
        execute_update_query(
            self.pool, 
            query, 
            user_id=user_id, 
            question_index=question_index,
        )

    async def get_statistic(self, user_id):
        query = f"""
            DECLARE $user_id AS Uint64;

            SELECT amount
            FROM quiz_state
            WHERE user_id=$user_id;
        """
        results = execute_select_query(self.pool, query, user_id=user_id)

        if len(results) == 0:
            return 0
        if results[0]["amount"] is None:
            return 0
        return results[0]["amount"]  

    async def update_statistic(self, user_id, amount):
        query = f"""
            DECLARE $user_id    AS Uint64;
            DECLARE $amount     AS Uint64;

            UPSERT INTO quiz_state (user_id, amount) VALUES ($user_id, $amount);
        """

        
        execute_update_query(
            self.pool, 
            query, 
            user_id=user_id, 
            amount=amount
        )
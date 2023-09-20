import json
import time
import uuid
from typing import List

from fastapi import Form, Header, status, APIRouter
from pydantic import BaseModel
from sqlalchemy import select, delete
from fastapi.responses import Response

from .consts import sessions, async_session, TEST_USERNAME, PokerContest, PokerGame, PokerResult

poker = APIRouter()


class Poker(BaseModel):
    user_id: str
    money: int


@poker.post("/poker/contest/{id}", status_code=status.HTTP_200_OK)
async def new_game(
        response: Response,
        id: str,
        users: List[Poker],
        authorization: str = Header(),
):
    #print(game.contestants)
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "poker.game.write" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    async with async_session() as session:
        contest = (await session.execute(select(PokerContest).filter_by(id=id))).first()
        if contest is None or contest[0] is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return
        contest = contest[0]

        game_id = str(uuid.uuid4())

        contestants_in_contest = json.loads(contest.contestants)

        for user in users:
            if user.user_id not in contestants_in_contest:
                response.status_code = status.HTTP_409_CONFLICT
                return "User is not in the contest"
            poker_result = PokerResult(id=str(uuid.uuid4()), game_id=game_id, user_id=user.user_id, money=int(user.money))
            session.add(poker_result)

        poker_game = PokerGame(id=game_id, contest_id=id, initializer=account_session.username,
                               played_at=int(time.time()))
        session.add(poker_game)

        await session.commit()


@poker.post("/poker/contests", status_code=status.HTTP_200_OK)
async def new_contest(
        response: Response,
        contestants: str = Form(),
        name: str = Form(),
        description: str = Form(""),
        minimum_bid: int = Form(),
        is_private: bool = Form(),
        has_ended: bool = Form(),
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "poker.contests.write" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    async with async_session() as session:
        cs = json.loads(contestants)
        for i in cs:
            if len(i.split(".")) != 2:
                response.status_code = status.HTTP_400_BAD_REQUEST
                return
        if account_session.username not in cs:
            cs.append(account_session.username)
        contest = PokerContest(
            id=str(uuid.uuid4()),
            contestants=json.dumps(cs),
            name=name,
            description=description,
            minimum_bet=max(minimum_bid, 0),
            is_private=is_private,
            has_ended=has_ended,
        )

        session.add(contest)
        await session.commit()


@poker.get("/poker/contests", status_code=status.HTTP_200_OK)
async def my_contests(
        response: Response,
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "poker.read" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    async with async_session() as session:
        contests = (await session.execute(select(PokerContest))).all()
        contests_user = []
        contests_public = []
        for contest in contests:
            contest = contest[0]
            contestants = json.loads(contest.contestants)
            if account_session.username in contestants:
                contests_user.append(contest)
            elif not contest.is_private:
                contests_public.append(contest)
        return {"my_contests": contests_user, "public_contests": contests_public}


@poker.delete("/poker/game/{id}", status_code=status.HTTP_200_OK)
async def delete_game(
        response: Response,
        id: str,
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "poker.game.delete" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    async with async_session() as session:
        game = (await session.execute(select(PokerGame).filter_by(id=id))).first()
        contest = (await session.execute(select(PokerContest).filter_by(id=game[0].contest_id))).first()
        if account_session.username not in json.loads(contest[0].contestants):
            response.status_code = status.HTTP_403_FORBIDDEN
            return
        await session.execute(delete(PokerResult).where(PokerResult.game_id == id))
        await session.execute(delete(PokerGame).where(PokerGame.id == id))
        await session.commit()


@poker.delete("/poker/contest/{id}", status_code=status.HTTP_200_OK)
async def delete_contest(
        response: Response,
        id: str,
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "poker.contests.delete" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    async with async_session() as session:
        contest = (await session.execute(select(PokerContest).filter_by(id=id))).first()
        contest = contest[0]
        if account_session.username not in json.loads(contest.contestants):
            response.status_code = status.HTTP_403_FORBIDDEN
            return
        games = await session.execute(select(PokerGame).where(PokerGame.contest_id == id))
        for game in games:
            await session.execute(delete(PokerResult).where(PokerResult.game_id == game[0].id))
            await session.execute(delete(PokerGame).where(PokerGame.id == game[0].id))
        await session.execute(delete(PokerContest).where(PokerContest.id == id))
        await session.commit()


@poker.patch("/poker/contest/{id}/add", status_code=status.HTTP_200_OK)
async def add_person(
        response: Response,
        id: str,
        person: str = Form(),
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "poker.contests.write" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    async with async_session() as session:
        contest = (await session.execute(select(PokerContest).filter(PokerContest.id == id))).first()
        contest = contest[0]
        contestants = json.loads(contest.contestants)
        if account_session.username not in contestants:
            response.status_code = status.HTTP_403_FORBIDDEN
            return
        if person not in contestants:
            contestants.append(person)
        contest.contestants = json.dumps(contestants)
        await session.commit()


@poker.post("/poker/contest/{id}/join", status_code=status.HTTP_200_OK)
async def join_contest(
        response: Response,
        id: str,
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "poker.contests.write" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    async with async_session() as session:
        contest = (await session.execute(select(PokerContest).filter(PokerContest.id == id))).first()
        contest = contest[0]
        contestants = json.loads(contest.contestants)
        if contest.is_private:
            response.status_code = status.HTTP_409_CONFLICT
            return
        if account_session.username not in contestants:
            contestants.append(account_session.username)
        contest.contestants = json.dumps(contestants)
        await session.commit()


@poker.patch("/poker/contest/{id}/private_public", status_code=status.HTTP_200_OK)
async def make_contest_private_or_public(
        response: Response,
        id: str,
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "poker.contests.write" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    async with async_session() as session:
        contest = (await session.execute(select(PokerContest).filter(PokerContest.id == id))).first()
        contest = contest[0]
        contestants = json.loads(contest.contestants)
        if account_session.username not in contestants:
            response.status_code = status.HTTP_403_FORBIDDEN
            return
        contest.is_private = not contest.is_private
        await session.commit()


@poker.delete("/poker/contest/{id}/remove", status_code=status.HTTP_200_OK)
async def remove_person(
        response: Response,
        id: str,
        person: str = Form(),
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "poker.contests.write" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    async with async_session() as session:
        contest = (await session.execute(select(PokerContest).filter(PokerContest.id == id))).first()
        contest = contest[0]
        contestants = json.loads(contest.contestants)
        if account_session.username not in contestants:
            response.status_code = status.HTTP_403_FORBIDDEN
            return
        contestants.remove(person)
        contest.contestants = json.dumps(contestants)
        await session.commit()


@poker.get("/poker/contest/{id}", status_code=status.HTTP_200_OK)
async def contest(
        response: Response,
        id: str,
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.oauth2_session and "poker.read" not in account_session.permissions:
        response.status_code = status.HTTP_403_FORBIDDEN
        return
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    async with async_session() as session:
        contest = (await session.execute(select(PokerContest).filter_by(id=id))).first()
        #print(contest, id)
        if contest is None or contest[0] is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return
        contest = contest[0]
        contestants = json.loads(contest.contestants)
        if account_session.username not in contestants:
            response.status_code = status.HTTP_403_FORBIDDEN
            return

        statistics: dict[str, dict] = {}
        all_contestants: dict[str, dict] = {}

        games = (await session.execute(select(PokerGame).filter_by(contest_id=id).order_by(PokerGame.played_at.asc()))).all()

        for contestant in contestants:
            all_contestants[contestant] = {"name": contestant, "total": 1000}
            if statistics.get(contestant) is None:
                statistics[contestant] = {
                    "iger_odigranih": 0,
                    "iger_zmaganih": 0,
                    "iger_izgubljenih": 0,
                    "razmerje_zmaganih_iger": 0.0,
                    "points_overtime": [1000],
                    "tock_skupaj": 1000,
                }

        cs2 = contestants

        games_json = []
        for game in games:
            game = game[0]
            contestants_json = {}
            contestants = (await session.execute(select(PokerResult).filter_by(game_id=game.id))).all()

            for contestant in cs2:
                statistics[contestant]["points_overtime"].append(statistics[contestant]["points_overtime"][-1])

            warning = False

            for contestant in contestants:
                contestant: PokerResult = contestant[0]

                if contestant.user_id not in cs2:
                    # Welp, it has happened
                    # Somebody has deleted a person.
                    warning = True
                    continue

                if contestant.money != 0:
                    statistics[contestant.user_id]["iger_odigranih"] += 1

                contestants_json[contestant.user_id] = {"money": contestant.money}
                statistics[contestant.user_id]["tock_skupaj"] += contestant.money
                all_contestants[contestant.user_id]["total"] += contestant.money
                statistics[contestant.user_id]["points_overtime"][-1] += contestant.money

                if contestant.money < 0:
                    statistics[contestant.user_id]["iger_izgubljenih"] += 1
                elif contestant.money > 0:
                    statistics[contestant.user_id]["iger_zmaganih"] += 1

                if statistics[contestant.user_id]["iger_odigranih"] != 0:
                    statistics[contestant.user_id]["razmerje_zmaganih_iger"] = statistics[contestant.user_id]["iger_zmaganih"] / statistics[contestant.user_id]["iger_odigranih"]
            games_json.append({"id": game.id, "contestants": contestants_json, "warning": warning})

        #print(statistics)
        return {"games": games_json, "name": contest.name, "description": contest.description, "id": contest.id,
                "status": all_contestants, "contestants": contest.contestants, "statistics": statistics,
                "is_private": contest.is_private, "minimum_bet": contest.minimum_bet}

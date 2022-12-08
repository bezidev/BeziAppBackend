import json
import time
import uuid

from fastapi import Form, Header, status, APIRouter
from sqlalchemy import select
from fastapi.responses import Response

from .consts import sessions, async_session, TarotContest, TarotGamePlayer, TarotGame, GAMEMODES


tarot = APIRouter()


@tarot.post("/tarot/contest/:id", status_code=status.HTTP_200_OK)
async def new_game(
        response: Response, contest_id: str,
        gamemode: int = Form(),
        trula_zbral: str = Form(),
        trula_napovedal: str = Form(),
        kralji_zbral: str = Form(),
        kralji_napovedal: str = Form(),
        pagat_zbral: str = Form(),
        pagat_napovedal: str = Form(),
        kralj_zbral: str = Form(),
        kralj_napovedal: str = Form(),
        valat_zbral: str = Form(),
        valat_napovedal: str = Form(),
        barvni_valat_zbral: str = Form(),
        barvni_valat_napovedal: str = Form(),
        contestants: str = Form(),
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    gimsis_session = sessions[authorization]

    async with async_session() as session:
        contest = (await session.execute(select(TarotContest).filter_by(id=id))).first()
        if contest is None or contest[0] is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return
        contest = contest[0]

        game_id = str(uuid.uuid4())

        contestants_in_contest = json.loads(contest.contestants)

        j = json.loads(contestants)

        if len(j) > 4 or len(j) < 3:
            response.status_code = status.HTTP_409_CONFLICT
            return

        v_tri = len(j) == 3

        for contestant in j:
            if contestant["username"] not in contestants_in_contest:
                continue
            contestant_id = str(uuid.uuid4())
            contestant_db = TarotGamePlayer(id=contestant_id, game_id=game_id, name=contestant["username"], difference=int(contestant["difference"]), playing=contestant["playing"])
            session.add(contestant_db)

        game = TarotGame(
            id=game_id,
            contest_id=contest_id,
            gamemode=gamemode,
            trulo_zbral=trula_zbral,
            trulo_napovedal=trula_napovedal,
            kralji_zbral=kralji_zbral,
            kralji_napovedal=kralji_napovedal,
            pagat_zbral=pagat_zbral,
            pagat_napovedal=pagat_napovedal,
            kralj_zbral=kralj_zbral,
            kralj_napovedal=kralj_napovedal,
            valat_zbral=valat_zbral,
            valat_napovedal=valat_napovedal,
            barvni_valat_zbral=barvni_valat_zbral,
            barvni_valat_napovedal=barvni_valat_napovedal,
            v_tri=v_tri,
            initializer=gimsis_session.username,
            played_at=int(time.time()),
        )

        session.add(game)
        await session.commit()


@tarot.post("/tarot/contests", status_code=status.HTTP_200_OK)
async def new_contest(
        response: Response,
        contestants: str = Form(),
        name: str = Form(),
        description: str = Form(),
        is_private: bool = Form(),
        has_ended: bool = Form(),
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    gimsis_session = sessions[authorization]

    async with async_session() as session:
        cs = json.loads(contestants)
        for i in cs:
            if len(i.split(".")) != 2:
                response.status_code = status.HTTP_400_BAD_REQUEST
                return
        contest = TarotContest(
            id=str(uuid.uuid4()),
            contestants=contestants,
            name=name,
            description=description,
            is_private=is_private,
            has_ended=has_ended,
        )

        session.add(contest)
        await session.commit()


@tarot.get("/tarot/contests", status_code=status.HTTP_200_OK)
async def my_contests(
        response: Response,
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    gimsis_session = sessions[authorization]

    async with async_session() as session:
        contests = (await session.execute(select(TarotContest))).all()
        contests_user = []
        for contest in contests:
            contestants = json.loads(contest.contestants)
            if gimsis_session.username not in contestants:
                continue
            contests_user.append(contest)
        return contests_user


@tarot.get("/tarot/contest/:id", status_code=status.HTTP_200_OK)
async def my_contests(
        response: Response,
        id: str = Header(),
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    gimsis_session = sessions[authorization]

    async with async_session() as session:
        contest = (await session.execute(select(TarotContest).filter_by(id=id))).first()
        if contest is None or contest[0] is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return
        contest = contest[0]
        contestants = json.loads(contest.contestants)
        if gimsis_session.username not in contestants:
            response.status_code = status.HTTP_403_FORBIDDEN
            return

        radlci: dict[str, int] = {}

        all_contestants = {}

        games = (await session.execute(select(TarotGame).filter_by(contest_id=id))).all()
        games_json = []
        for game in games:
            game = game[0]
            contestants_json = {}
            contestants = (await session.execute(select(TarotGamePlayer).filter_by(game_id=game.id))).all()
            for contestant in contestants:
                contestant = contestant[0]
                difference = contestant.difference

                contestants_json[contestant.name] = {"radlc_uporabljen": False, "radlci_status": 0, "razlika": 0}

                # jah, se zgodi
                if radlci.get(contestant.name) is None:
                    radlci[contestant.name] = 0

                if contestant.playing:
                    # bog ne daj, da dobiš minusa
                    if difference <= 0:
                        contestant -= GAMEMODES[game.gamemode]
                    else:
                        contestant += GAMEMODES[game.gamemode]

                    # omg don't bully me for this logic
                    if game.trulo_zbral != "":
                        if game.trulo_zbral == "igralci":
                            if game.trulo_napovedal == "igralci":
                                difference += 20
                            else:
                                difference += 10
                        else:
                            if game.trulo_napovedal != "":
                                difference -= 20
                            else:
                                difference -= 10

                    if game.kralji_zbral != "":
                        if game.kralji_zbral == "igralci":
                            if game.kralji_napovedal == "igralci":
                                difference += 20
                            else:
                                difference += 10
                        else:
                            if game.kralji_napovedal != "":
                                difference -= 20
                            else:
                                difference -= 10

                    if game.pagat_zbral != "":
                        if game.pagat_zbral == "igralci":
                            if game.pagat_napovedal == "igralci":
                                difference += 20
                            else:
                                difference += 10
                        else:
                            if game.pagat_napovedal != "":
                                difference -= 20
                            else:
                                difference -= 10

                    if game.kralj_zbral != "":
                        if game.kralj_zbral == "igralci":
                            if game.kralj_napovedal == "igralci":
                                difference += 20
                            else:
                                difference += 10
                        else:
                            if game.kralj_napovedal != "":
                                difference -= 20
                            else:
                                difference -= 10

                    # no, valat in barvni valat nista +=, temveč sta =, saj pol ne bi nihče igral gamemodov razen v primeru odprtega berača
                    if game.valat_zbral != "":
                        if game.valat_zbral == "igralci":
                            if game.valat_napovedal == "igralci":
                                difference = 500
                            else:
                                difference = 250
                        else:
                            if game.valat_napovedal != "":
                                difference = -500
                            else:
                                difference = -250

                    if game.barvni_valat_zbral != "":
                        if game.barvni_valat_zbral == "igralci":
                            if game.barvni_valat_napovedal == "igralci":
                                difference = 250
                            else:
                                difference = 125
                        else:
                            if game.barvni_valat_napovedal != "":
                                difference = -250
                            else:
                                difference = -125

                    # lol let's boost the difference (radlci go brrrrrrrrrrrrrrrrrrrrrrr)
                    if radlci[contestant.name] > 0:
                        difference *= 2
                        if difference > 0:
                            radlci[contestant.name] -= 1
                            contestants_json[contestant.name]["radlc_uporabljen"] = True

                # dejmo radlce vsem tem bogim ljudem
                if 7 <= game.gamemode <= 12:
                    radlci[contestant.name] += 1

                contestants_json[contestant.name]["radlci_status"] = radlci[contestant.name]
                contestants_json[contestant.name]["razlika"] = difference

                if all_contestants.get(contestant.name) is None:
                    all_contestants[contestant.name] = {"name": contestant.name, "total": difference, "radlci_status": radlci[contestant.name]}

                all_contestants[contestant.name]["radlci_status"] = radlci[contestant.name]
                all_contestants[contestant.name]["total"] += difference
            games_json.append({"id": game.id, "type": game.gamemode, "contestants": contestants_json})
        return {"games": games, "name": contest.name, "description": contest.description, "id": contest.id, "status": all_contestants}

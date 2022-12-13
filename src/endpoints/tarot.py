import json
import time
import uuid

from fastapi import Form, Header, status, APIRouter
from pydantic import BaseModel
from sqlalchemy import select, delete
from fastapi.responses import Response

from .consts import sessions, async_session, TarotContest, TarotGamePlayer, TarotGame, GAMEMODES

tarot = APIRouter()


class TarotGameAPI(BaseModel):
    gamemode: int
    trula_zbral: str
    trula_napovedal: str
    kralji_zbral: str
    kralji_napovedal: str
    pagat_zbral: str
    pagat_napovedal: str
    kralj_zbral: str
    kralj_napovedal: str
    valat_zbral: str
    valat_napovedal: str
    barvni_valat_zbral: str
    barvni_valat_napovedal: str
    contestants: str
    izgubil_monda: str


class PersonAPI(BaseModel):
    person: str


@tarot.post("/tarot/contest/{id}", status_code=status.HTTP_200_OK)
async def new_game(
        response: Response,
        id: str,
        game: TarotGameAPI,
        authorization: str = Header(),
):
    print(game.contestants)
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

        j = json.loads(game.contestants)

        if len(j) > 4 or len(j) < 3:
            response.status_code = status.HTTP_409_CONFLICT
            return "Cannot play with less than 3 players or more than 4 players."

        v_tri = len(j) == 3

        for contestant in j:
            if contestant["username"] not in contestants_in_contest:
                continue
            contestant_id = str(uuid.uuid4())
            contestant_db = TarotGamePlayer(id=contestant_id, game_id=game_id, name=contestant["username"],
                                            difference=int(contestant["difference"]), playing=contestant["playing"])
            session.add(contestant_db)

        g = TarotGame(
            id=game_id,
            contest_id=id,
            gamemode=game.gamemode,
            trulo_zbral=game.trula_zbral,
            trulo_napovedal=game.trula_napovedal,
            kralji_zbral=game.kralji_zbral,
            kralji_napovedal=game.kralji_napovedal,
            pagat_zbral=game.pagat_zbral,
            pagat_napovedal=game.pagat_napovedal,
            kralj_zbral=game.kralj_zbral,
            kralj_napovedal=game.kralj_napovedal,
            valat_zbral=game.valat_zbral,
            valat_napovedal=game.valat_napovedal,
            barvni_valat_zbral=game.barvni_valat_zbral,
            barvni_valat_napovedal=game.barvni_valat_napovedal,
            izgubil_monda=game.izgubil_monda,
            v_tri=v_tri,
            initializer=gimsis_session.username,
            played_at=int(time.time()),
        )

        session.add(g)
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
        if gimsis_session.username not in cs:
            cs.append(gimsis_session.username)
        contest = TarotContest(
            id=str(uuid.uuid4()),
            contestants=json.dumps(cs),
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
        contests_public = []
        for contest in contests:
            contest = contest[0]
            contestants = json.loads(contest.contestants)
            if gimsis_session.username in contestants:
                contests_user.append(contest)
            elif not contest.is_private:
                contests_public.append(contest)
        return {"my_contests": contests_user, "public_contests": contests_public}


@tarot.delete("/tarot/game/{id}", status_code=status.HTTP_200_OK)
async def delete_game(
        response: Response,
        id: str,
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    gimsis_session = sessions[authorization]

    async with async_session() as session:
        game = (await session.execute(select(TarotGame).filter_by(id=id))).first()
        contest = (await session.execute(select(TarotContest).filter_by(id=game[0].contest_id))).first()
        if gimsis_session.username not in json.loads(contest[0].contestants):
            response.status_code = status.HTTP_403_FORBIDDEN
            return
        await session.execute(delete(TarotGamePlayer).where(TarotGamePlayer.game_id == id))
        await session.execute(delete(TarotGame).where(TarotGame.id == id))
        await session.commit()


@tarot.delete("/tarot/contest/{id}", status_code=status.HTTP_200_OK)
async def delete_contest(
        response: Response,
        id: str,
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    gimsis_session = sessions[authorization]

    async with async_session() as session:
        contest = (await session.execute(select(TarotContest).filter_by(id=id))).first()
        contest = contest[0]
        if gimsis_session.username not in json.loads(contest.contestants):
            response.status_code = status.HTTP_403_FORBIDDEN
            return
        games = await session.execute(select(TarotGame).where(TarotGame.contest_id == id))
        for game in games:
            await session.execute(delete(TarotGamePlayer).where(TarotGamePlayer.game_id == game[0].id))
            await session.execute(delete(TarotGame).where(TarotGame.id == game[0].id))
        await session.execute(delete(TarotContest).where(TarotContest.id == id))
        await session.commit()


@tarot.patch("/tarot/contest/{id}/add", status_code=status.HTTP_200_OK)
async def add_person(
        response: Response,
        id: str,
        person: PersonAPI,
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    gimsis_session = sessions[authorization]

    async with async_session() as session:
        contest = (await session.execute(select(TarotContest).filter(TarotContest.id == id))).first()
        contest = contest[0]
        contestants = json.loads(contest.contestants)
        if contest.is_private:
            if gimsis_session.username not in contestants:
                response.status_code = status.HTTP_403_FORBIDDEN
                return
            if person not in contestants:
                contestants.append(person.person)
            contest.contestants = json.dumps(contestants)
            await session.commit()
        else:
            if gimsis_session.username in contestants:
                response.status_code = status.HTTP_409_CONFLICT
                return
            contestants.append(gimsis_session.username)
            contest.contestants = json.dumps(contestants)
            await session.commit()


@tarot.delete("/tarot/contest/{id}/remove", status_code=status.HTTP_200_OK)
async def remove_person(
        response: Response,
        id: str,
        person: PersonAPI,
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    gimsis_session = sessions[authorization]

    async with async_session() as session:
        contest = (await session.execute(select(TarotContest).filter(TarotContest.id == id))).first()
        contest = contest[0]
        contestants = json.loads(contest.contestants)
        if gimsis_session.username not in contestants:
            response.status_code = status.HTTP_403_FORBIDDEN
            return
        contestants.remove(person.person)
        contest.contestants = json.dumps(contestants)
        await session.commit()


@tarot.get("/tarot/contest/{id}", status_code=status.HTTP_200_OK)
async def contest(
        response: Response,
        id: str,
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    gimsis_session = sessions[authorization]

    async with async_session() as session:
        contest = (await session.execute(select(TarotContest).filter_by(id=id))).first()
        print(contest, id)
        if contest is None or contest[0] is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return
        contest = contest[0]
        contestants = json.loads(contest.contestants)
        if gimsis_session.username not in contestants:
            response.status_code = status.HTTP_403_FORBIDDEN
            return

        radlci: dict[str, int] = {}

        statistics = {}

        all_contestants = {}

        games = (await session.execute(select(TarotGame).filter_by(contest_id=id).order_by(TarotGame.played_at.asc()))).all()

        for contestant in contestants:
            all_contestants[contestant] = {"name": contestant, "total": 0, "radlci_status": 0}

        cs2 = contestants

        games_json = []
        for game in games:
            game = game[0]
            contestants_json = {}
            contestants = (await session.execute(select(TarotGamePlayer).filter_by(game_id=game.id))).all()

            #omg this code is bloat & unreadable
            for contestant in cs2:
                if statistics.get(contestant) is None:
                    statistics[contestant] = {
                        "iger_odigranih": 0,
                        "iger_igral": 0,
                        "iger_zmagal": 0,
                        "tock_skupaj": 0,
                        "tipi_iger": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                        "points_overtime": [0],
                    }
                ok = False
                for cs in contestants:
                    if cs[0].name == contestant:
                        ok = True
                        break
                if ok:
                    continue
                print(contestant)
                statistics[contestant]["points_overtime"].append(statistics[contestant]["points_overtime"][-1])

            for contestant in contestants:
                contestant = contestant[0]
                difference = contestant.difference

                statistics[contestant.name]["iger_odigranih"] += 1

                contestants_json[contestant.name] = {"radlc_uporabljen": False, "radlci_status": 0, "razlika": 0}

                # jah, se zgodi
                if radlci.get(contestant.name) is None:
                    radlci[contestant.name] = 0

                if game.gamemode == 12:
                    for con in contestants:
                        # Če nekdo pobere vsaj polovico točk, je avtomatično dobil -70, medtem ko vsi ostali 0
                        if abs(con[0].difference) >= 35:
                            if contestant.name != con[0].name:
                                difference = 0
                            else:
                                difference = -70
                    difference = -abs(difference)

                # pri klopu se ne igra
                if contestant.playing or game.gamemode == 12:
                    statistics[contestant.name]["iger_igral"] += 1
                    statistics[contestant.name]["tipi_iger"][game.gamemode] += 1

                if contestant.playing:
                    # haha renons
                    if game.gamemode != 13:
                        # bog ne daj, da dobiš minusa
                        if game.gamemode == 3 or game.gamemode == 7 or 9 <= game.gamemode <= 11:
                            # pri beračih + pikolu in valatih se ne šteje kok si pobral
                            # temveč samo če si uspešno dokončal gamemode
                            if difference <= 0:
                                difference = -GAMEMODES[game.gamemode]
                            else:
                                difference = GAMEMODES[game.gamemode]
                        else:
                            if difference <= 0:
                                difference -= GAMEMODES[game.gamemode]
                            else:
                                difference += GAMEMODES[game.gamemode]

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
                    else:
                        difference = -70

                # lol let's boost the difference (radlci go brrrrrrrrrrrrrrrrrrrrrrr)
                if radlci[contestant.name] > 0 and difference != 0 and game.gamemode != 13:
                    difference *= 2
                    if difference > 0:
                        radlci[contestant.name] -= 1
                        contestants_json[contestant.name]["radlc_uporabljen"] = True

                # izguba monda
                if contestant.name == game.izgubil_monda:
                    difference -= 21

                # dejmo radlce vsem tem bogim ljudem
                if 7 <= game.gamemode <= 12:
                    radlci[contestant.name] += 1

                contestants_json[contestant.name]["radlci_status"] = radlci[contestant.name]
                contestants_json[contestant.name]["razlika"] = difference

                statistics[contestant.name]["tock_skupaj"] += difference
                if difference > 0:
                    statistics[contestant.name]["iger_zmagal"] += 1

                statistics[contestant.name]["points_overtime"].append(statistics[contestant.name]["points_overtime"][-1] + difference)

                if all_contestants.get(contestant.name) is None:
                    all_contestants[contestant.name] = {"name": contestant.name, "total": 0,
                                                        "radlci_status": radlci[contestant.name]}

                all_contestants[contestant.name]["radlci_status"] = radlci[contestant.name]
                all_contestants[contestant.name]["total"] += difference
            games_json.append({"id": game.id, "type": game.gamemode, "contestants": contestants_json})
        print(statistics)
        return {"games": games_json, "name": contest.name, "description": contest.description, "id": contest.id,
                "status": all_contestants, "contestants": contest.contestants, "statistics": statistics}

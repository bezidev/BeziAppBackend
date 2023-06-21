import json
import time
import uuid

from fastapi import Form, Header, status, APIRouter
from pydantic import BaseModel
from sqlalchemy import select, delete
from fastapi.responses import Response

from .consts import sessions, async_session, TarotContest, TarotGamePlayer, TarotGame, GAMEMODES, TEST_USERNAME

tarot = APIRouter()


class TarotGameAPI(BaseModel):
    gamemode: int
    igra_kontre: int
    trula_zbral: str
    trula_napovedal: str
    trula_kontre: int
    kralji_zbral: str
    kralji_napovedal: str
    kralji_kontre: int
    pagat_zbral: str
    pagat_napovedal: str
    pagat_kontre: int
    kralj_zbral: str
    kralj_napovedal: str
    kralj_kontre: int
    valat_zbral: str
    valat_napovedal: str
    valat_kontre: int
    #barvni_valat_zbral: str
    #barvni_valat_napovedal: str
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
    #print(game.contestants)
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

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

        # verifikacija konter
        if 0 > game.igra_kontre or game.igra_kontre > 4:
            response.status_code = status.HTTP_406_NOT_ACCEPTABLE
            return "Kontra ni veljavna"

        if 0 > game.trula_kontre or game.trula_kontre > 4:
            response.status_code = status.HTTP_406_NOT_ACCEPTABLE
            return "Kontra ni veljavna"

        if 0 > game.kralji_kontre or game.kralji_kontre > 4:
            response.status_code = status.HTTP_406_NOT_ACCEPTABLE
            return "Kontra ni veljavna"

        if 0 > game.pagat_kontre or game.pagat_kontre > 4:
            response.status_code = status.HTTP_406_NOT_ACCEPTABLE
            return "Kontra ni veljavna"

        if 0 > game.kralj_kontre or game.kralj_kontre > 4:
            response.status_code = status.HTTP_406_NOT_ACCEPTABLE
            return "Kontra ni veljavna"

        if 0 > game.valat_kontre or game.valat_kontre > 4:
            response.status_code = status.HTTP_406_NOT_ACCEPTABLE
            return "Kontra ni veljavna"

        g = TarotGame(
            id=game_id,
            contest_id=id,
            gamemode=game.gamemode,
            igra_kontre=game.igra_kontre,
            trulo_zbral=game.trula_zbral,
            trulo_napovedal=game.trula_napovedal,
            trula_kontre=game.trula_kontre,
            kralji_zbral=game.kralji_zbral,
            kralji_napovedal=game.kralji_napovedal,
            kralji_kontre=game.kralji_kontre,
            pagat_zbral=game.pagat_zbral,
            pagat_napovedal=game.pagat_napovedal,
            pagat_kontre=game.pagat_kontre,
            kralj_zbral=game.kralj_zbral,
            kralj_napovedal=game.kralj_napovedal,
            kralj_kontre=game.kralj_kontre,
            valat_zbral=game.valat_zbral,
            valat_napovedal=game.valat_napovedal,
            valat_kontre=game.valat_kontre,
            barvni_valat_zbral="",
            barvni_valat_napovedal="",
            izgubil_monda=game.izgubil_monda,
            v_tri=v_tri,
            initializer=account_session.username,
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
    account_session = sessions[authorization]
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
    account_session = sessions[authorization]

    async with async_session() as session:
        contests = (await session.execute(select(TarotContest))).all()
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


@tarot.delete("/tarot/game/{id}", status_code=status.HTTP_200_OK)
async def delete_game(
        response: Response,
        id: str,
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    async with async_session() as session:
        game = (await session.execute(select(TarotGame).filter_by(id=id))).first()
        contest = (await session.execute(select(TarotContest).filter_by(id=game[0].contest_id))).first()
        if account_session.username not in json.loads(contest[0].contestants):
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
    account_session = sessions[authorization]
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    async with async_session() as session:
        contest = (await session.execute(select(TarotContest).filter_by(id=id))).first()
        contest = contest[0]
        if account_session.username not in json.loads(contest.contestants):
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
    account_session = sessions[authorization]
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    async with async_session() as session:
        contest = (await session.execute(select(TarotContest).filter(TarotContest.id == id))).first()
        contest = contest[0]
        contestants = json.loads(contest.contestants)
        if account_session.username not in contestants:
            response.status_code = status.HTTP_403_FORBIDDEN
            return
        if person not in contestants:
            contestants.append(person.person)
        contest.contestants = json.dumps(contestants)
        await session.commit()


@tarot.post("/tarot/contest/{id}/join", status_code=status.HTTP_200_OK)
async def join_contest(
        response: Response,
        id: str,
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    async with async_session() as session:
        contest = (await session.execute(select(TarotContest).filter(TarotContest.id == id))).first()
        contest = contest[0]
        contestants = json.loads(contest.contestants)
        if contest.is_private:
            response.status_code = status.HTTP_409_CONFLICT
            return
        if account_session.username not in contestants:
            contestants.append(account_session.username)
        contest.contestants = json.dumps(contestants)
        await session.commit()


@tarot.patch("/tarot/contest/{id}/private_public", status_code=status.HTTP_200_OK)
async def make_contest_private_or_public(
        response: Response,
        id: str,
        authorization: str = Header(),
):
    if authorization == "" or sessions.get(authorization) is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return
    account_session = sessions[authorization]
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    async with async_session() as session:
        contest = (await session.execute(select(TarotContest).filter(TarotContest.id == id))).first()
        contest = contest[0]
        contestants = json.loads(contest.contestants)
        if account_session.username not in contestants:
            response.status_code = status.HTTP_403_FORBIDDEN
            return
        contest.is_private = not contest.is_private
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
    account_session = sessions[authorization]
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    async with async_session() as session:
        contest = (await session.execute(select(TarotContest).filter(TarotContest.id == id))).first()
        contest = contest[0]
        contestants = json.loads(contest.contestants)
        if account_session.username not in contestants:
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
    account_session = sessions[authorization]
    if account_session.username == TEST_USERNAME:
        response.status_code = status.HTTP_403_FORBIDDEN
        return

    async with async_session() as session:
        contest = (await session.execute(select(TarotContest).filter_by(id=id))).first()
        #print(contest, id)
        if contest is None or contest[0] is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return
        contest = contest[0]
        contestants = json.loads(contest.contestants)
        if account_session.username not in contestants:
            response.status_code = status.HTTP_403_FORBIDDEN
            return

        radlci: dict[str, int] = {}

        statistics = {}

        all_contestants = {}

        games = (await session.execute(select(TarotGame).filter_by(contest_id=id).order_by(TarotGame.played_at.asc()))).all()

        for contestant in contestants:
            all_contestants[contestant] = {"name": contestant, "total": 0, "radlci_status": 0}
            if statistics.get(contestant) is None:
                statistics[contestant] = {
                    "iger_odigranih": 0,
                    "iger_igral": 0,
                    "iger_zmagal": 0,
                    "tock_skupaj": 0,
                    "tipi_iger": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                    "points_overtime": [0],
                }

        cs2 = contestants

        games_json = []
        for game in games:
            game = game[0]
            contestants_json = {}
            contestants = (await session.execute(select(TarotGamePlayer).filter_by(game_id=game.id))).all()

            # omg this code is bloat & unreadable
            for contestant in cs2:
                ok = False
                for cs in contestants:
                    if cs[0].name == contestant:
                        ok = True
                        break
                if ok:
                    continue
                # print(contestant)
                statistics[contestant]["points_overtime"].append(statistics[contestant]["points_overtime"][-1])

            explanation: dict[str, list] = {}

            warning = False

            # ma dej nehi na klopa se ne štejejo kontre
            if game.gamemode == 12:
                picked_up_more = False
                for con in contestants:
                    con = con[0]
                    if con.difference >= 35:
                        picked_up_more = True
                        break
                for i, con in enumerate(contestants):
                    con = con[0]
                    explanation[con.name] = []

                    # Če nekdo pobere vsaj polovico točk, je avtomatično dobil -70, medtem ko vsi ostali 0
                    # prav tako, če dve osebi pobereta 35, ostali pa 0, se morata obe osebi ki sta pobrali šteti kot -70.
                    if not picked_up_more:
                        if con.difference == 0:
                            explanation[con.name].append({"title": "Igra (pobral nič)", "diff": 70, "kontra": 1})
                            contestants[i][0].difference = 70
                        else:
                            explanation[con.name].append({"title": "Razlika", "diff": -abs(con.difference), "kontra": 1})
                            contestants[i][0].difference = -abs(con.difference)
                    else:
                        if abs(con.difference) >= 35:
                            explanation[con.name].append({"title": f"Igra (pobral {abs(con.difference)})", "diff": -70, "kontra": 1})
                            contestants[i][0].difference = -70
                        elif con.difference == 0:
                            explanation[con.name].append({"title": "Igra (pobral nič)", "diff": 70, "kontra": 1})
                            contestants[i][0].difference = 70
                        else:
                            explanation[con.name].append({"title": f"Igra (nekdo pobral več kot 34, pobral {abs(con.difference)})", "diff": 0, "kontra": 1})
                            contestants[i][0].difference = 0

            for contestant in contestants:
                contestant = contestant[0]
                difference = contestant.difference

                if explanation.get(contestant.name) is None:
                    explanation[contestant.name] = []

                if contestant.name not in cs2:
                    # Welp, it has happened
                    # Somebody has deleted a person.
                    warning = True
                    continue

                statistics[contestant.name]["iger_odigranih"] += 1

                contestants_json[contestant.name] = {"radlc_uporabljen": False, "radlci_status": 0, "razlika": 0, "igra": contestant.playing}

                # jah, se zgodi
                if radlci.get(contestant.name) is None:
                    radlci[contestant.name] = 0

                # pri klopu se ne igra
                if contestant.playing or game.gamemode == 12:
                    statistics[contestant.name]["iger_igral"] += 1
                    statistics[contestant.name]["tipi_iger"][game.gamemode] += 1

                if contestant.playing:
                    kontra = 2 ** game.igra_kontre

                    # bog ne daj, da dobiš minusa
                    if game.gamemode == 3 or 7 <= game.gamemode <= 11 or game.gamemode == 13:
                        if game.gamemode == 13:
                            # na renons NI KONTRE
                            difference = -70
                            explanation[contestant.name].append({"title": "Igra", "diff": difference, "kontra": kontra})
                        else:
                            # pri beračih + pikolu, solo brez in valatih se ne šteje kok si pobral
                            # temveč samo če si uspešno dokončal gamemode
                            if difference <= 0:
                                difference = -GAMEMODES[game.gamemode] * kontra
                            else:
                                difference = GAMEMODES[game.gamemode] * kontra
                            explanation[contestant.name].append({"title": "Igra", "diff": difference, "kontra": kontra})
                    else:
                        gamemode = GAMEMODES[game.gamemode]
                        if difference <= 0:
                            gamemode = -gamemode
                        difference *= kontra
                        gamemode *= kontra
                        explanation[contestant.name].append({"title": "Igra", "diff": gamemode, "kontra": kontra})
                        explanation[contestant.name].append({"title": "Razlika", "diff": difference, "kontra": kontra})
                        difference += gamemode

                        # omg don't bully me for this logic
                        if game.trulo_zbral != "":
                            # Tukaj naredimo nepredstavljivo – potenco števila 2. V primeru, da ni kontre je dan
                            # argument tako ali tako nič, kar essentially pomeni, da je to dva na nič, kar je ena [
                            # citation needed], kar naj na tem svetu ne bi spremenilo rezultata pri množenju. Zdaj,
                            # lahko bi to šel dokazovat (a je namenilnik prav? Ne vem ne sprašuj o moji slovenščini),
                            # da je to res, če bi želel zabijati čas, kakor smo to delali v prvem letniku pri
                            # matematiki, ampak se mi iskreno ne da in bom zato to prepustil bralcu oz. zdravi kmečki
                            # pameti. Hvala za razumevanje.
                            kontra = 2**game.trula_kontre
                            if game.trulo_zbral == "igralci":
                                if game.trulo_napovedal == "igralci":
                                    diff = 20 * kontra
                                    explanation[contestant.name].append({"title": "Napovedana trula", "diff": diff, "kontra": kontra})
                                    difference += diff
                                else:
                                    diff = 10 * kontra
                                    explanation[contestant.name].append({"title": "Nenapovedana trula", "diff": diff, "kontra": kontra})
                                    difference += diff
                            else:
                                if game.trulo_napovedal != "":
                                    diff = -20 * kontra
                                    explanation[contestant.name].append({"title": "Napovedana trula", "diff": diff, "kontra": kontra})
                                    difference += diff
                                else:
                                    diff = -10 * kontra
                                    explanation[contestant.name].append({"title": "Nenapovedana trula", "diff": diff, "kontra": kontra})
                                    difference += diff

                        if game.kralji_zbral != "":
                            kontra = 2 ** game.kralji_kontre
                            if game.kralji_zbral == "igralci":
                                if game.kralji_napovedal == "igralci":
                                    diff = 20 * kontra
                                    explanation[contestant.name].append({"title": "Napovedani kralji", "diff": diff, "kontra": kontra})
                                    difference += diff
                                else:
                                    diff = 10 * kontra
                                    explanation[contestant.name].append({"title": "Nenapovedani kralji", "diff": diff, "kontra": kontra})
                                    difference += diff
                            else:
                                if game.kralji_napovedal != "":
                                    diff = -20 * kontra
                                    explanation[contestant.name].append({"title": "Napovedani kralji", "diff": diff, "kontra": kontra})
                                    difference += diff
                                else:
                                    diff = -10 * kontra
                                    explanation[contestant.name].append({"title": "Nenapovedani kralji", "diff": diff, "kontra": kontra})
                                    difference += diff

                        if game.pagat_zbral != "":
                            kontra = 2 ** game.pagat_kontre
                            if game.pagat_zbral == "igralci":
                                if game.pagat_napovedal == "igralci":
                                    diff = 50 * kontra
                                    explanation[contestant.name].append({"title": "Napovedan pagat ultimo", "diff": diff, "kontra": kontra})
                                    difference += diff
                                else:
                                    diff = 25 * kontra
                                    explanation[contestant.name].append({"title": "Nenapovedan pagat ultimo", "diff": diff, "kontra": kontra})
                                    difference += diff
                            else:
                                if game.pagat_napovedal != "":
                                    diff = -50 * kontra
                                    explanation[contestant.name].append({"title": "Napovedan pagat ultimo", "diff": diff, "kontra": kontra})
                                    difference += diff
                                else:
                                    diff = -25 * kontra
                                    explanation[contestant.name].append({"title": "Nenapovedan pagat ultimo", "diff": diff, "kontra": kontra})
                                    difference += diff

                        if game.kralj_zbral != "":
                            kontra = 2 ** game.kralj_kontre
                            if game.kralj_zbral == "igralci":
                                if game.kralj_napovedal == "igralci":
                                    diff = 20 * kontra
                                    explanation[contestant.name].append({"title": "Napovedan kralj ultimo", "diff": diff, "kontra": kontra})
                                    difference += diff
                                else:
                                    diff = 10 * kontra
                                    explanation[contestant.name].append({"title": "Nenapovedan kralj ultimo", "diff": diff, "kontra": kontra})
                                    difference += diff
                            else:
                                if game.kralj_napovedal != "":
                                    diff = -20 * kontra
                                    explanation[contestant.name].append({"title": "Napovedan kralj ultimo", "diff": diff, "kontra": kontra})
                                    difference += diff
                                else:
                                    diff = -10 * kontra
                                    explanation[contestant.name].append({"title": "Nenapovedan kralj ultimo", "diff": diff, "kontra": kontra})
                                    difference += diff

                        # no, valat in barvni valat nista +=, temveč sta =, saj pol ne bi nihče igral gamemodov razen v primeru odprtega berača
                        if game.valat_zbral != "":
                            kontra = 2 ** game.valat_kontre
                            explanation[contestant.name] = []
                            if game.valat_zbral == "igralci":
                                if game.valat_napovedal == "igralci":
                                    diff = 500 * kontra
                                    difference = diff
                                else:
                                    diff = 250 * kontra
                                    difference = diff
                            else:
                                if game.valat_napovedal != "":
                                    diff = -500 * kontra
                                    difference = diff
                                else:
                                    diff = -250 * kontra
                                    difference = diff
                            explanation[contestant.name].append({"title": "Igra", "diff": difference, "kontra": kontra})

                        """
                        torej, po uradnih tarok pravilih, barvni valat ni napoved, temveč samo in izključno IGRA.
                        
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
                        """

                    has_inputed = True

                # lol let's boost the difference (radlci go brrrrrrrrrrrrrrrrrrrrrrr)
                if radlci[contestant.name] > 0 and difference != 0 and game.gamemode != 13:
                    difference *= 2
                    if difference > 0:
                        radlci[contestant.name] -= 1
                    contestants_json[contestant.name]["radlc_uporabljen"] = True

                # izguba monda
                if contestant.name == game.izgubil_monda:
                    explanation[contestant.name].append({"title": "Izguba monda", "diff": -21, "kontra": 1})
                    difference -= 21

                # dejmo radlce vsem tem bogim ljudem
                if 7 <= game.gamemode <= 12 or game.gamemode == 15:
                    radlci[contestant.name] += 1

                contestants_json[contestant.name]["radlci_status"] = radlci[contestant.name]
                contestants_json[contestant.name]["razlika"] = difference

                statistics[contestant.name]["tock_skupaj"] += difference
                if difference > 0:
                    statistics[contestant.name]["iger_zmagal"] += 1

                statistics[contestant.name]["points_overtime"].append(statistics[contestant.name]["points_overtime"][-1] + difference)

                if all_contestants.get(contestant.name) is None:
                    all_contestants[contestant.name] = {"name": contestant.name, "total": 0, "total_radlci": 0,
                                                        "radlci_status": radlci[contestant.name]}

                all_contestants[contestant.name]["radlci_status"] = radlci[contestant.name]
                all_contestants[contestant.name]["total"] += difference
            games_json.append({"id": game.id, "type": game.gamemode, "contestants": contestants_json, "warning": warning, "explanation": explanation})

        for i in all_contestants.keys():
            all_contestants[i]["total_radlci"] = all_contestants[i]["total"] + all_contestants[i]["radlci_status"] * -40

        #print(statistics)
        return {"games": games_json, "name": contest.name, "description": contest.description, "id": contest.id,
                "status": all_contestants, "contestants": contest.contestants, "statistics": statistics,
                "is_private": contest.is_private}

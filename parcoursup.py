from typing import Optional
import bs4
from dataclasses import dataclass
import requests as rq

session = rq.Session()


@dataclass
class QueueData:
    ranking: int
    queue_ranking: int
    queue_len: int
    last_sent: int
    last_admitted: int

    @classmethod
    def from_html(cls, soup: bs4.BeautifulSoup):
        queue = soup.find('ul')
        queue_ranking, queue_len = [int(t.text)
                                    for t in queue.select("li > b")]
        ranking_data = list(soup.select(".fr-alert > ul")[0].children)
        ranking_data = list(filter(lambda x: x != '\n', ranking_data))

        ranking = ranking_data[1].select("p > b")[0].text
        last_admitted = ranking_data[3].find('b').text
        last_sent = ranking_data[2].find('b').text
        ranking, last_admitted, last_sent = int(
            ranking), int(last_admitted), int(last_sent)
        return cls(ranking, queue_ranking, queue_len, last_sent, last_admitted)


@dataclass
class BoardingData:
    ranking: int
    places: int
    last_sent: int

    @property
    def queue_ranking(self):
        return self.ranking - self.last_sent

    @classmethod
    def from_html(cls, soup: bs4.BeautifulSoup):
        boarding_data = list(soup.select(".fr-alert > ul")[0].children)
        boarding_data = list(filter(lambda x: x != '\n', boarding_data))
        places, ranking = boarding_data[0].find(
            'b').text, boarding_data[2].find('b').text
        places, ranking = int(places), int(ranking)

        last_sent = boarding_data[3].find('p').text.split(' ')[-1]
        last_sent = int(last_sent)
        return cls(ranking, places, last_sent)


@dataclass
class WishData:
    school: str
    school_type: str
    status: str
    soup: bs4.BeautifulSoup

    @property
    def data_url(self):
        data_js = self.soup.find(
            text="Infos sur la liste d’attente").parent['onclick']
        return "https://dossierappel.parcoursup.fr/Candidat/"+data_js[data_js.find("admissions"):data_js.find("\',")]

    @property
    def full_name(self):
        s_type = self.school_type
        if "internat" in s_type:
            i = s_type.find("internat")
            s_type = s_type[:i-8] + s_type[i+8:]
        return self.school + ' ' + s_type

    @classmethod
    def from_html(cls, html: bs4.BeautifulSoup):
        school = html.find("p", {"class": "psup-wish-card__school"}).text
        school_type = html.find("p", {"class": "psup-wish-card__course"}).text
        status = html.find(text="Statut").parent.parent.find('p').text
        return cls(school, school_type, status, html)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} school=\"{self.school}\" school_type=\"{self.school_type}\" status=\"{self.status}\">"

    def __str__(self) -> str:
        return repr(self)

    def __eq__(self, __value: object) -> bool:
        return (self.status, self.school, self.school_type) == (__value.status, __value.school, __value.school_type)


@dataclass
class Wish:
    wishData: WishData
    boarding: bool
    queueData: Optional[QueueData]
    boardingData: Optional[BoardingData]

    @classmethod
    def from_html(cls, soup: bs4.BeautifulSoup | None, boardingSoup: Optional[bs4.BeautifulSoup] = None):
        w_data = None
        bw_data = None
        queueData = None
        boardingData = None

        if soup:
            w_data = WishData.from_html(soup)
            if w_data.status.lower() == "en attente":
                queue_url = w_data.data_url
                r = session.get(queue_url)
                queueData = QueueData.from_html(
                    bs4.BeautifulSoup(r.content, features="html.parser"))

        if boardingSoup:
            bw_data = WishData.from_html(boardingSoup)
            if bw_data.status.lower() != "en attente":
                boardingData = None
            else:
                boarding_url = bw_data.data_url
                r = session.get(boarding_url)
                boardingData = BoardingData.from_html(
                    bs4.BeautifulSoup(r.content, features="html.parser"))

        return cls(w_data if w_data else bw_data, bool(boardingSoup), queueData, boardingData)

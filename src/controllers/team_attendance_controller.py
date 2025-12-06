from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List

from models.models import Event, AccessCategory
from models.responses.responses import UserAttendanceResponse, UserAttendance, AttendanceResponse


class TeamAttendanceControlling(ABC):
    @abstractmethod
    async def retrieve_upcoming_events(self, user_id: int, from_date: date) -> List[Event]:
        pass

    @abstractmethod
    async def retrieve_team_attendance(self, event_id: int) -> UserAttendanceResponse:
        pass


class TeamAttendanceController(TeamAttendanceControlling):
    async def retrieve_upcoming_events(self, user_id: int, from_date: date) -> List[Event]:
        raise NotImplementedError

    async def retrieve_team_attendance(self, event_id: int) -> UserAttendanceResponse:
        raise NotImplementedError


class FakeTeamAttendanceController(TeamAttendanceControlling):
    def __init__(self):
        self.sample_event = Event(
            id=1,
            title="Field Training",
            description="Saturday training session",
            start=datetime(2025, 10, 11, 13, 30),
            end=datetime(2025, 10, 11, 15, 0),
            is_event_locked=False,
            is_accountable=True,
            access_category=AccessCategory.MEMBER,
        )

    async def retrieve_upcoming_events(self, user_id: int, from_date: date) -> List[Event]:
        return [self.sample_event]

    async def retrieve_team_attendance(self, event_id: int) -> UserAttendanceResponse:
        male_attending = [
            UserAttendance(name="Aaron Seah", telegram_user="aaronseah", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason="Late 2pm, beach")),
            UserAttendance(name="Aaron Toh", telegram_user="aarontoh", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason=None)),
            UserAttendance(name="Alvin Song", telegram_user="alvinsong", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason="training before training")),
            UserAttendance(name="Anurag", telegram_user="anurag", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason="late funeral")),
            UserAttendance(name="Ben Lui", telegram_user="benlui", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason="late,210")),
            UserAttendance(name="Ethan Kok", telegram_user="ethankok", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason=None)),
            UserAttendance(name="Isaac Sekkappan", telegram_user="isaac", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason=None)),
            UserAttendance(name="KianBoon", telegram_user="kianboon", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason=None)),
            UserAttendance(name="Lee Ling Zhen", telegram_user="llz", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason="late from marc's workout")),
            UserAttendance(name="Owen Lim", telegram_user="owenlim", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason=None)),
            UserAttendance(name="Russell Tay", telegram_user="russellt", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason=None)),
            UserAttendance(name="Ryan Lee", telegram_user="ryanlee", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason="probs not training much knee")),
            UserAttendance(name="Seah Jiale", telegram_user="sjiale", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason="Late, from marc workout")),
            UserAttendance(name="Shine", telegram_user="shine", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason="Late work (230)")),
            UserAttendance(name="Sun Hao Ting", telegram_user="sht", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason=None)),
            UserAttendance(name="Tow Jia Hao", telegram_user="jiahao", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason=None)),
            UserAttendance(name="Wafir Hakim", telegram_user="wafir", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason=None)),
            UserAttendance(name="Wei Kiat", telegram_user="weikiat", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason=None)),
            UserAttendance(name="Zx", telegram_user="zx", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason=None)),
        ]

        female_attending = [
            UserAttendance(name="Amanda Lunardhi", telegram_user="amanda", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason=None)),
            UserAttendance(name="Brina Ong", telegram_user="brina", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason=None)),
            UserAttendance(name="Catherine Lee", telegram_user="catherine", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason=None)),
            UserAttendance(name="Denise Huang", telegram_user="deniseh", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason=None)),
            UserAttendance(name="Denise Yang", telegram_user="denisey", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason="Reaching 230pmish! Coming from work")),
            UserAttendance(name="Javier Chua Yun Dong", telegram_user="javier", gender="F", access=AccessCategory.GUEST, attendance=AttendanceResponse(status=True, reason="2pm")),
            UserAttendance(name="Jerilyn Hui", telegram_user="jerilyn", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason=None)),
            UserAttendance(name="Jermaine Yam", telegram_user="jermaine", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason=None)),
            UserAttendance(name="Jia Qi", telegram_user="jiaq", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason=None)),
            UserAttendance(name="Livana Ho", telegram_user="livana", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason="2pm late")),
            UserAttendance(name="Micole", telegram_user="micole", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason="late, marc's bday thing")),
            UserAttendance(name="Zhang Wanyi", telegram_user="wanyi", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason=None)),
            UserAttendance(name="chiang su lynn", telegram_user="sulynn", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=True, reason="late (family lunch, 215)")),
        ]

        absent = [
            UserAttendance(name="Jordan Lee", telegram_user="jordan", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=False, reason="Reservist")),
            UserAttendance(name="Matthew Lou", telegram_user="matthew", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=False, reason="just touched down, got wedding to attend")),
            UserAttendance(name="Oliver Chang", telegram_user="oliver", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=False, reason="NYC")),
            UserAttendance(name="Qi Qian Hao", telegram_user="qqh", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=False, reason="In aus")),
            UserAttendance(name="Tan Jing Xiang", telegram_user="jingxiang", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=False, reason="Studyin")),
            UserAttendance(name="Charlotte Ho", telegram_user="charlotte", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=False, reason="🛸")),
            UserAttendance(name="Felis Tan", telegram_user="felis", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=False, reason="Sick :()")),
            UserAttendance(name="Gin Tan", telegram_user="gintan", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=False, reason="Thighs are still strained from a work incident……. 🙃")),
            UserAttendance(name="Jerlyn Ng", telegram_user="jerlyn", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=False, reason="Work trip")),
            UserAttendance(name="Mary Tan", telegram_user="mary", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=False, reason="Rest")),
            UserAttendance(name="Samantha Kong", telegram_user="samantha", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=False, reason="T")),
            UserAttendance(name="Thea Tim", telegram_user="thea", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=False, reason="Injured")),
            UserAttendance(name="Tricia Bek", telegram_user="tricia", gender="F", access=AccessCategory.GUEST, attendance=AttendanceResponse(status=False, reason="🇨🇦🍁")),
        ]

        unindicated = [
            UserAttendance(name="Glenn", telegram_user="glenn", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=None, reason=None)),
            UserAttendance(name="Ivan Ng", telegram_user="ivan", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=None, reason=None)),
            UserAttendance(name="Keane Lim", telegram_user="keanel", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=None, reason=None)),
            UserAttendance(name="Keane Ng", telegram_user="keanen", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=None, reason=None)),
            UserAttendance(name="Lucas Tiong", telegram_user="lucas", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=None, reason=None)),
            UserAttendance(name="Marc Lee", telegram_user="marc", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=None, reason=None)),
            UserAttendance(name="Max Liaw", telegram_user="max", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=None, reason=None)),
            UserAttendance(name="ng kaiwen", telegram_user="kaiwen", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=None, reason=None)),
            UserAttendance(name="Roy Kang", telegram_user="roy", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=None, reason=None)),
            UserAttendance(name="Sam", telegram_user="sam", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=None, reason=None)),
            UserAttendance(name="Samuel Lee", telegram_user="samuell", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=None, reason=None)),
            UserAttendance(name="Sean Chui", telegram_user="sean", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=None, reason=None)),
            UserAttendance(name="Tan Tek Wei", telegram_user="tekwei", gender="M", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=None, reason=None)),
            UserAttendance(name="Chloe Ng", telegram_user="chloe", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=None, reason=None)),
            UserAttendance(name="Eunice Lim", telegram_user="eunice", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=None, reason=None)),
            UserAttendance(name="Germaine Lee", telegram_user="germaine", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=None, reason=None)),
            UserAttendance(name="Gigi Koh", telegram_user="gigi", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=None, reason=None)),
            UserAttendance(name="Janel Lau", telegram_user="janel", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=None, reason=None)),
            UserAttendance(name="Jia Hui", telegram_user="jiahui", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=None, reason=None)),
            UserAttendance(name="Renee Neo", telegram_user="renee", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=None, reason=None)),
            UserAttendance(name="Vivian Chan", telegram_user="vivian", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=None, reason=None)),
            UserAttendance(name="Wendy Lim", telegram_user="wendy", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=None, reason=None)),
            UserAttendance(name="Xiao Ho", telegram_user="xiao", gender="F", access=AccessCategory.MEMBER, attendance=AttendanceResponse(status=None, reason=None)),
            UserAttendance(name="Royce Chen", telegram_user="royce", gender="M", access=AccessCategory.GUEST, attendance=AttendanceResponse(status=None, reason="checking things out")),
        ]

        return UserAttendanceResponse(
            male=male_attending,
            female=female_attending,
            absent=absent,
            unindicated=unindicated,
        )

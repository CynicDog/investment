"""Weekly DCA tracker issue: five Mon–Fri checkboxes the user ticks once Toss confirms each fill."""

from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel, Field, model_validator


WeekdayName = Literal["Mon", "Tue", "Wed", "Thu", "Fri"]
WEEKDAY_NAMES: tuple[WeekdayName, ...] = ("Mon", "Tue", "Wed", "Thu", "Fri")


class DCATick(BaseModel):
    weekday: WeekdayName
    on_date: date
    confirmed: bool = False


class DCATracker(BaseModel):
    week_of: date = Field(description="Monday of the week being tracked.")
    ticks: list[DCATick] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def _shape(self) -> "DCATracker":
        if self.week_of.weekday() != 0:
            raise ValueError(f"week_of must be a Monday, got {self.week_of} (weekday={self.week_of.weekday()})")
        for i, t in enumerate(self.ticks):
            expected_name = WEEKDAY_NAMES[i]
            expected_date = self.week_of + timedelta(days=i)
            if t.weekday != expected_name:
                raise ValueError(f"ticks[{i}].weekday must be '{expected_name}', got '{t.weekday}'")
            if t.on_date != expected_date:
                raise ValueError(f"ticks[{i}].on_date must be {expected_date}, got {t.on_date}")
        return self

    @classmethod
    def fresh(cls, week_of: date) -> "DCATracker":
        """Build an unticked tracker for the given Monday."""
        return cls(
            week_of=week_of,
            ticks=[
                DCATick(
                    weekday=WEEKDAY_NAMES[i],
                    on_date=week_of + timedelta(days=i),
                    confirmed=False,
                )
                for i in range(5)
            ],
        )

    @property
    def confirmed_count(self) -> int:
        return sum(1 for t in self.ticks if t.confirmed)

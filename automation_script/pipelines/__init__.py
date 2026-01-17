# automation_script/pipelines/__init__.py

from .base import BasePipeline, ApplicationResult, UnhandledField
from .greenhouse import GreenhousePipeline
from .lever import LeverPipeline
from .workable import WorkablePipeline
from .workday import WorkdayPipeline

__all__ = [
    "BasePipeline",
    "ApplicationResult",
    "UnhandledField",
    "GreenhousePipeline",
    "LeverPipeline",
    "WorkablePipeline",
    "WorkdayPipeline",
]

# ATS platform detection mapping
ATS_PLATFORMS = {
    "greenhouse.io": GreenhousePipeline,
    "lever.co": LeverPipeline,
    "workable.com": WorkablePipeline,
    "myworkdayjobs.com": WorkdayPipeline,
}


def get_pipeline_for_url(url: str):
    """
    Detect the ATS platform from a job URL and return the appropriate pipeline class.
    Returns None if no matching pipeline is found.
    """
    url_lower = url.lower()
    for domain, pipeline_class in ATS_PLATFORMS.items():
        if domain in url_lower:
            return pipeline_class
    return None

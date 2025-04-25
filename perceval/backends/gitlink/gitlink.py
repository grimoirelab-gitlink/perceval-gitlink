import requests
import json
import logging
import configparser

from perceval.client import HttpClient, RateLimitHandler
from grimoirelab_toolkit.uris import urijoin
from grimoirelab_toolkit.datetime import (
    datetime_to_utc,
    str_to_datetime,
    datetime_utcnow,
)
from perceval.backend import (
    Backend,
    DEFAULT_SEARCH_FIELD,
    BackendCommand,
    BackendCommandArgumentParser,
)
from perceval.utils import DEFAULT_DATETIME, DEFAULT_LAST_DATETIME

GITLINK_URL = "https://www.gitlink.org.cn"
GITLINK_TOKEN_URL = "https://www.gitlink.org.cn/oauth/token"
GITLINK_API_URL = "https://www.gitlink.org.cn/api/v1"

MIN_RATE_LIMIT = 10
MAX_RATE_LIMIT = 500

TOKEN_USAGE_BEFORE_SWITCH = 0.1
MAX_CATEGORY_ITEMS_PER_PAGE = 5
PER_PAGE = 5

DEFAULT_SEARCH_FIELD = "item_id"
DEFAULT_SLEEP_TIME = 1  # pre set
MAX_RETRIES = 5

CATEGORY_ISSUE = "issue"
CATEGORY_PULL_REQUEST = "pull_request"
CATEGORY_REPO = "repository"
TARGET_ISSUE_FIELDS = ["author", "assignee"]

logger = logging.getLogger(__name__)


class Gitlink(Backend):
    """Gitlink backend for Perceval"""

    version = "0.1.0"
    CATEGORIES = [CATEGORY_ISSUE, CATEGORY_PULL_REQUEST, CATEGORY_REPO]

    def __init__(
        self,
        owner=None,
        repository=None,
        api_token=None,
        base_url=None,
        tag=None,
        archive=None,
        sleep_for_rate=False,
        min_rate_to_sleep=MIN_RATE_LIMIT,
        max_retries=MAX_RETRIES,
        sleep_time=DEFAULT_SLEEP_TIME,
        max_items=MAX_CATEGORY_ITEMS_PER_PAGE,
        ssl_verify=True,
    ):
        if api_token is None:
            token = self._get_access_tokens()
            api_token = [token]
        origin = base_url if base_url else GITLINK_URL
        origin = urijoin(origin, owner, repository)

        super().__init__(origin, tag=tag, archive=archive, ssl_verify=ssl_verify)

        self.owner = owner
        self.repository = repository
        self.api_token = api_token
        self.base_url = base_url

        self.sleep_for_rate = sleep_for_rate
        self.min_rate_to_sleep = min_rate_to_sleep
        self.max_retries = max_retries
        self.sleep_time = sleep_time
        self.max_items = max_items

        self.client = None
        self.exclude_user_data = False  # whether should collect the user information
        self._users = {}  # internal users cache

    def search_fields(self, item):
        """Add search fields to an item.

        It adds the values of `metadata_id` plus the `owner` and `repo`.

        :param item: the item to extract the search fields values

        :returns: a dict of search fields
        """
        search_fields = {
            DEFAULT_SEARCH_FIELD: self.metadata_id(item),
            "owner": self.owner,
            "repo": self.repository,
        }

        return search_fields

    def fetch(
        self,
        category=CATEGORY_ISSUE,
        filter_classified=False,
        from_date=DEFAULT_DATETIME,
        to_date=DEFAULT_LAST_DATETIME,
    ):
        """Fetch the issues/pull requests from the repository.

        :param category: the category of items to fetch
        :param filter_classified: remove classified fields from the resulting items
        :param from_date: obtain issues/pull requests updated since this date
        :param to_date: obtain issues/pull requests until a specific date (included)

        :returns: a generator of issues
        """
        self.exclude_user_data = filter_classified

        if not from_date:
            from_date = DEFAULT_DATETIME
        if not to_date:
            to_date = DEFAULT_LAST_DATETIME

        from_date = datetime_to_utc(from_date)
        to_date = datetime_to_utc(to_date)
        kwargs = {"from_date": from_date, "to_date": to_date}
        items = super().fetch(
            category=category, filter_classified=filter_classified, **kwargs
        )

        return items

    def fetch_items(self, category, **kwargs):
        """Fetch the items (issues or pull_requests or repo infomation)
        :params category: the category of items to fetch
        :params kwargs: backend arguments

        :returns: a generator of items
        """
        from_date = kwargs["from_date"]
        to_date = kwargs["to_date"]
        if category == CATEGORY_ISSUE:
            items = self.__fetch_issues()
        elif category == CATEGORY_PULL_REQUEST:
            items = self.__fetch_pull_requests()
        else:
            items = self.__fetch_repo_info()
        return items

    @classmethod
    def has_archiving(cls):
        return True

    @classmethod
    def has_resuming(cls):
        return True

    @staticmethod
    def metadata_id(item):
        """Extracts the identifier from a Gitlink item."""
        if "forked_count" in item:
            return str(item["repo_id"])
        else:
            return str(item["id"])
        """This func needs to be checked """

    @staticmethod
    def metadata_updated_on(item):
        """Extracts the update time from a Gitlink item.

        The timestamp used is extracted from 'updated_at' field.
        This date s convert to UNIX timestamp format.

        :param item: item generated by the backend

        :returns: a UNIX timestamp
        """
        if "fetched_on" in item:
            return item["fetched_on"]
        else:
            str_time = item["updated_at"]
            time = str_to_datetime(str_time)

            return time.timestamp()

    @staticmethod
    def metadata_category(item):
        """Extracts the category from a Gitlink item."""

        if "subject" in item:
            category = CATEGORY_ISSUE
        elif "title" in item:
            category = CATEGORY_PULL_REQUEST
        elif "releases" in item:
            category = CATEGORY_REPO
        return category

    def search_fields(self, item):
        search_fields = {
            DEFAULT_SEARCH_FIELD: self.metadata_id(item),
            "owner": self.owner,
            "repo": self.repository,
        }

        return search_fields

    def _init_client(self):
        """Init clinet"""
        return GitlinkClient(self.owner, self.repository, self.api_token, self.base_url)

    def __fetch_issues(self):
        """Fetch the issues"""
        issues_groups = (
            self.client.issue_list()
        )  # gitlink don't fetch issues_list by time

        for raw_issues in issues_groups:
            issues = json.loads(raw_issues)
            for issue in issues["issues"]:
                self.__init_extra_issue_field(issue)
                certain_issue = self.__fetch_issue(issue["id"])
                issue["comments_data"] = self.__fetch_issue_comments(issue["id"])
                issue["description"] = certain_issue["description"]
                issue["subject"] = certain_issue["subject"]
                issue["description"] = certain_issue["description"]
                issue["created_at"] = certain_issue["created_at"]
                issue["updated_at"] = certain_issue["updated_at"]
                issue["blockchain_token_num"] = certain_issue["blockchain_token_num"]
                issue["branchname"] = certain_issue["branch_name"]
                issue["start_date"] = certain_issue["start_date"]
                issue["due_date"] = certain_issue["due_date"]
                issue["assignee"] = certain_issue["assigners"]
                issue["status"] = certain_issue["status"]
                issue["participants"] = certain_issue["participants"]
                issue["priority"] = certain_issue["priority"]
                issue["operate_journals_count"] = certain_issue[
                    "operate_journals_count"
                ]
                issue["attachments"] = certain_issue["attachments"]
                yield issue

    def __fetch_pull_requests(self):
        """Fetch pull requests"""

        raw_pulls_groups = self.client.pulls()
        for raw_pulls in raw_pulls_groups:
            pulls = json.loads(raw_pulls)["pulls"]
            for pull in pulls:
                # self.__init_extra_pull_field
                certain_pull = self.__fetch_certain_pull_request(pull["id"])
                fetched_on = datetime_utcnow()
                certain_pull["fetched_on"] = fetched_on.timestamp()
                certain_pull["comments"] = self.__fetch_pull_review_comments(pull["id"])

                yield certain_pull

    def __fetch_certain_pull_request(self, index):
        """Fetch certain pull request by index"""
        certain_pull = self.client.pull(index)
        return json.loads(certain_pull)

    def __fetch_pull_review_comments(self, index):
        """Fetch certain pull review comments"""
        pull_review = self.client.pull_review_comments(index)
        return json.loads(pull_review)

    def __fetch_repo_info(self):
        """Fetch repository information"""
        repo_info = self.client.repo()
        repo_info = json.loads(repo_info)
        self.__init_extra_repo_field(repo_info)
        releases = self.client.repo_releases()
        releases = json.loads(releases)
        for release in releases["releases"]:
            repo_info["releases"].append(release)
        fetched_on = datetime_utcnow()
        repo_info["fetched_on"] = fetched_on.timestamp()
        yield repo_info
        """emm, I used 'fetch' instead of 'fetch_items', so just iterate for one time"""

    def __fetch_issue_comments(self, index):
        """Get issue comments"""

        # comments = []
        groupe_comments = self.client.issue_comments(index)
        for group_comment in groupe_comments:
            comment = json.loads(group_comment)["journals"]
            # comments.append(comment)
            return comment

    def __fetch_issue(self, index):
        """Get an issue by index"""
        issue = self.client.issue(index)

        return json.loads(issue)
        # return self.client.fetch_data("issues",index)

    def __init_extra_issue_field(self, issue):
        """Add fields to an issue"""
        issue["author_data"] = {}
        issue["assignee_data"] = {}
        issue["comments_data"] = []
        issue["description"] = ""
        issue["branchname"] = ""
        issue["start_date"] = ""
        issue["due_date"] = ""
        issue["assignee"] = {}
        issue["operate_journals_count"] = ""
        issue["attachments"] = {}
        """wait wait, I have not goten clear the formats of new fields"""

    def __init_extra_repo_field(self, repo):
        """Add fields to a repo"""
        repo["releases"] = []
        repo["fetched_on"] = []

    # def __init_extra_pull_field(self,pull):

    def _get_access_tokens(self):
        """Get an access token for initialing without tokens"""
        config = configparser.ConfigParser()
        config.read("config.ini")

        # 从配置文件中获取CLIENT_ID和CLIENT_SECRET
        client_id = config["credentials"]["client_id"]
        client_secret = config["credentials"]["client_secret"]
        payload = json.dumps(
            {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            }
        )

        headers = {
            "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
            "Content-Type": "application/json",
        }

        response = requests.request(
            "POST", GITLINK_TOKEN_URL, data=payload, headers=headers
        )
        responses = response.json()

        return responses["access_token"]


class GitlinkClient(HttpClient):
    """Client for retrieving information from GitLink API
    :param owner: Gitlink owner
    :param repository: Gitlink repository from the owner
    :param base_url: Gitlink URL in enterprise edition case
    :param sleep_for_rate
    :param min_rate_to_sleep
    :param sleep_time
    :param max_retries
    :param max_items
    :param archive :  collect issues that already tetrievd from an archive
    :param from_archive
    :param ssl_verify
    """

    EXTRA_STATUS_FORCELIST = [403, 500, 502, 503]

    # initial the client for gitlink
    def __init__(
        self,
        owner,
        repository,
        tokens,
        base_url=None,
        sleep_time=DEFAULT_SLEEP_TIME,
        sleep_for_rate=False,
        min_rate_to_sleep=MIN_RATE_LIMIT,
        max_retries=MAX_RETRIES,
        max_items=MAX_CATEGORY_ITEMS_PER_PAGE,
        archive=None,
        from_archive=False,
        ssl_verify=True,
    ):
        self.owner = owner
        self.repository = repository
        # take the frist token for initialing
        if tokens:
            self.access_token = tokens[0]
        else:
            self.access_token = self._get_access_tokens()
        # I'm not sure whether Gitlink have limits or not, maybe change later
        self.last_rate_limit_checked = None
        self.max_items = max_items

        # initial the url for API
        if base_url == None:
            base_url = "https://www.gitlink.org.cn/api/v1"

        else:
            base_url = urijoin(base_url, "api", "v1")

        super().__init__(
            base_url,
            sleep_time=sleep_time,
            max_retries=max_retries,
            extra_status_forcelist=self.EXTRA_STATUS_FORCELIST,
            archive=archive,
            from_archive=from_archive,
            ssl_verify=ssl_verify,
        )
        # after the initial of the client, maybe should refresh the token

    def fetch_data(self, category, index):
        """Get cettain pull/issue from Gitlink"""
        path = urijoin(
            self.base_url, self.owner, self.repository, category, f"{index}.json"
        )
        response = self.fetch(path)
        return json.loads(response.text)

    def pull_review_comments(self, index):
        """Get pull review comments list"""
        payload = {"sort_direction": "asc"}
        url = urijoin(
            self.base_url, self.owner, self.repository, "pulls", index, "journals.json"
        )
        item = self.fetch(url=url, payload=payload)
        return item.text

    def pulls(self):
        """Get pulls request from Gitlink"""
        payload = {"sort_by": "created_at"}
        path = urijoin("pulls.json")
        item = self.fetch_items(path, payload=payload)
        return item

    def pull(self, index):
        """Get certain pull requests from Gitlink"""
        url = urijoin(
            self.base_url, self.owner, self.repository, "pulls", f"{index}.json"
        )
        item = self.fetch(url)
        return item.text

    def repo(self):
        """Get repository data"""
        base_url = "https://www.gitlink.org.cn/api"
        url = urijoin(base_url, self.owner, self.repository, "detail.json")
        item = self.fetch(url=url)
        return item.text

    def repo_releases(self):
        """Get repository releases data"""

        base_url = "https://www.gitlink.org.cn/api"
        url = urijoin(base_url, self.owner, self.repository, "releases.json")
        item = self.fetch(url=url)

        return item.text

    def collaborators(self, keyword=None):
        """Get collaborators of a project"""

        path = urijoin(self.base_url, self.owner, self.repository, "collaborators.json")
        if keyword:
            payload = {"keyword": keyword}
            item = self.fetch(path, payload).text
        else:
            item = self.fetch(path).text

        return item

    def milestones(self):
        """Get milestones of a repository"""

        payload = {"page": 1, "limit": PER_PAGE, "sort_directioin": "asc"}
        path = "milestones.json"

        return self.fetch_items(path, payload)

    def issue(self, index):
        """Get an issue by index"""

        path = urijoin(
            self.base_url, self.owner, self.repository, "issues", f"{index}.json"
        )
        item = self.fetch(path)

        return item.text

    def issue_childeren_comments(self, index, id):
        """Get the sub comments of a issue comment"""

        payload = {"page": 1, "limit": PER_PAGE, "sort_directioin": "asc"}
        path = urijoin("issues", index, "journals", id, "children_journals.json")

        return self.fetch_items(path, payload)

    def issue_comments(self, index):
        """Get the issue comments or operation log"""

        payload = {"page": 1, "limit": PER_PAGE, "sort_direction": "asc"}
        path = urijoin("issues", index, "journals.json")

        return self.fetch_items(path, payload)

    def issue_list(self):
        """Get the issue list"""

        payload = {"page": 1, "limit": PER_PAGE, "sort_direction": "asc"}
        path = urijoin("issues.json")

        return self.fetch_items(path, payload)

    def fetch(
        self,
        url,
        payload=None,
        headers=None,
        method=HttpClient.GET,
        stream=False,
        auth=False,
    ):
        """base mothod to fetch the data from the remote URL"""
        # Gitlink distinguish the differences between datas in headers instead of payload
        # however,it doesn't matter
        if self.access_token:
            if not headers:
                headers = {}
            headers["Authorization"] = self.access_token
            headers["User-Agent"] = "Apifox/1.0.0 (https://apifox.com)"
        response = super().fetch(url, payload, headers, method, stream, auth)
        # the method from class HttpClient

        return response

    def fetch_items(self, path, payload):
        """ "Return the items from gitlink API using links paination"""

        page = 1
        total_page = None
        url = urijoin(self.base_url, self.owner, self.repository, path)

        response = self.fetch(url, payload=payload)
        items = response.text
        limit = int(payload["limit"]) if "limit" in payload else PER_PAGE
        test = response.json()
        total_page = round(int(test["total_count"]) / limit)
        page += 1

        while items:
            yield items
            items = None
            if page <= total_page:  # I'm not understand what is the link in reponse
                payload["page"] = str(page)
                response = self.fetch(url, payload=payload)
                page += 1
                items = response.text

    # This part now can not work yet
    # def _refresh_access_tokens(self):
    #     """Send a refresh post access to the Gitee Server"""

    #     if self.access_token:
    #         url = (
    #             GITLINK_TOKEN_URL
    #             + "?grant_type=refresh_token&refresh_token="
    #             + self.access_token
    #         )
    #         self.session.post(url, data=None, headers=None)

    def _get_access_tokens(self):
        """Get an access token for initialing without tokens"""
        config = configparser.ConfigParser()
        config.read("config.ini")

        # 从配置文件中获取CLIENT_ID和CLIENT_SECRET
        client_id = config["credentials"]["client_id"]
        client_secret = config["credentials"]["client_secret"]
        payload = json.dumps(
            {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            }
        )

        headers = {
            "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
            "Content-Type": "application/json",
        }

        response = requests.request(
            "POST", GITLINK_TOKEN_URL, data=payload, headers=headers
        )
        responses = response.json()

        return responses["access_token"]


class GitlinkCommand(BackendCommand):
    """Class to run Gitlink backend from the command line"""

    BACKEND = Gitlink

    @classmethod
    def setup_cmd_parser(cls):
        """Returns the Gitlink argument parser."""

        parser = BackendCommandArgumentParser(
            cls.BACKEND,
            from_date=True,
            to_date=True,
            token_auth=False,
            archive=True,
            ssl_verify=True,
        )
        # Gitlink options
        group = parser.parser.add_argument_group("Gitlink arguments")
        group.add_argument(
            "--sleep-for-rate",
            dest="sleep_for_rate",
            action="store_true",
            help="sleep for getting more rate",
        )
        group.add_argument(
            "--min-rate-to-sleep",
            dest="min_rate_to_sleep",
            default=MIN_RATE_LIMIT,
            type=int,
            help="sleep until reset when the rate limit reaches this value",
        )

        # initial Gitlink API token list
        group.add_argument(
            "-t",
            "--api-token",
            dest="api_token",
            nargs="+",
            default=[],
            help="list of Gitlink API tokens",
        )

        group.add_argument(
            "--max-items",
            dest="max_items",
            default=MAX_CATEGORY_ITEMS_PER_PAGE,
            type=int,
            help="Max number of category items per query.",
        )

        group.add_argument(
            "--max-retries",
            dest="max_retries",
            default=MAX_RETRIES,
            type=int,
            help="number of API call retries",
        )
        group.add_argument(
            "--sleep-time",
            dest="sleep_time",
            default=DEFAULT_SLEEP_TIME,
            type=int,
            help="sleeping time between API call retries",
        )

        # Positional arguments
        parser.parser.add_argument("owner", help="Gitlink owner")
        parser.parser.add_argument("repository", help="Gitlink repository")

        return parser



import datetime
import os
import unittest
import httpretty

from perceval.backend import BackendCommandArgumentParser
from perceval.backends.gitlink.gitlink import (Gitlink, GitlinkClient,
                                            GitlinkCommand,CATEGORY_ISSUE,CATEGORY_REPO,CATEGORY_PULL_REQUEST
                                           )

from base import TestCaseBackendArchive
from perceval.utils import DEFAULT_DATETIME, DEFAULT_LAST_DATETIME


GITLINK_API_URL = "https://www.gitlink.org.cn/api"
GITLINK_API_URL2 = "https://www.gitlink.org.cn/api/v1"
GITLINK_REFRESH_TOKEN_URL = "https://www.gitlink.org.cn/oauth/token"
GITLINK_REPO_URL = GITLINK_API_URL + "/gitlink_example/repo/detail.json"
GITLINK_ISSUES_URL = GITLINK_API_URL + "/v1/gitlink_example/repo/issues.json"
GITLINK_ISSUE_COMMENTS_URL_1 = GITLINK_API_URL + "/v1/gitlink_example/repo/issues/1/journals.json"
GITLINK_ISSUE_COMMENTS_URL_2 = GITLINK_API_URL + "/v1/gitlink_example/repo/issues/2/journals.json"
GITLINK_PULL_REQUEST_URL = "https://www.gitlink.org.cn/api/v1/gitlink_example/repo/pulls.json"

GITLINK_PULL_REQUEST_1_COMMENTS_URL = "https://www.gitlink.org.cn/api/v1/gitlink_example/repo/pulls/1/journals.json"
GITLINK_PULL_REQUEST_1_COMMITS_URL = "https://www.gitlink.org.cn/api/gitlink_example/repo/pulls/1/commits.json"
GITLINK_PULL_REQUEST_2_COMMENTS_URL = "https://www.gitlink.org.cn/api/v1/gitlink_example/repo/pulls/2/journals.json"
GITLINK_PULL_REQUEST_2_COMMITS_URL = "https://www.gitlink.org.cn/api/gitlink_example/repo/pulls/2/commits.json"



def read_file(filename, mode='r'):
    with open(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), filename), mode) as f:
        content = f.read()
    return content

@httpretty.activate
def setup_gitlink_pull_request_services():
    setup_gitlink_basic_services()
    __setup_gitlink_pull_request_services()
    __setup_gitlink_pull_request_services_with_commits_and_comments
    __setup_gitlink_pull_request_services_with_empty_commits_and_comments

@httpretty.activate
def setup_gitlink_basic_services():
    setup_refresh_access_token_service()
    repo = read_file('data/gitlink//gitlink_repo')
    httpretty.register_uri(httpretty.GET, GITLINK_REPO_URL, body=repo, status=200)

@httpretty.activate
def setup_gitlink_issue_services():
    setup_gitlink_basic_services()
    __setup_gitlink_issue_services()

@httpretty.activate
def __setup_gitlink_issue_services():
    issues1 = read_file('data/gitlink//gitlink_issue')


    httpretty.register_uri(httpretty.GET, GITLINK_ISSUES_URL,
                           body=issues1, status=200,
                        )

    issue1_comments = read_file('data/gitlink//gitlink_issue_comments')
    httpretty.register_uri(httpretty.GET, GITLINK_ISSUE_COMMENTS_URL_1,
                           body=issue1_comments, status=200,
                           )
@httpretty.activate
def __setup_gitlink_pull_request_services():
    pull_request = read_file("data/gitlink//gitlink_pull_requests")

    httpretty.register_uri(httpretty.GET,GITLINK_PULL_REQUEST_URL,
                           body=pull_request,status=200)
    
@httpretty.activate
def __setup_gitlink_pull_request_services_with_commits_and_comments():
    
    pull_request_1_comments = read_file('data/gitlink//gitlink_pull_request_comments_1')
    httpretty.register_uri(httpretty.GET, GITLINK_PULL_REQUEST_1_COMMENTS_URL,
                           body=pull_request_1_comments, status=200
                           )
    pull_request_1_commits = read_file('data/gitlink//gitlink_pull_request_commit_1')
    httpretty.register_uri(httpretty.GET, GITLINK_PULL_REQUEST_1_COMMITS_URL,
                           body=pull_request_1_commits, status=200
                           )
    pull_request_2_comments = read_file('data/gitlink//gitlink_pull_request_comments_2')
    httpretty.register_uri(httpretty.GET, GITLINK_PULL_REQUEST_2_COMMENTS_URL,
                           body=pull_request_2_comments, status=200
                           )
    pull_request_2_commits = read_file('data/gitlink//gitlink_pull_request_commit_2')
    httpretty.register_uri(httpretty.GET, GITLINK_PULL_REQUEST_2_COMMITS_URL,
                           body=pull_request_2_commits, status=200
                           )
    
@httpretty.activate
def __setup_gitlink_pull_request_services_with_empty_commits_and_comments():
    comments_body = {
                        "total_count": 0,
                        "journals": []
                    }
    commit_body =   {
                        "commits_count": 2,
                        "commits": []
                    }
    httpretty.register_uri(httpretty.GET, GITLINK_PULL_REQUEST_1_COMMENTS_URL,
                           body=comments_body, status=200)
    httpretty.register_uri(httpretty.GET, GITLINK_PULL_REQUEST_1_COMMITS_URL,
                           body=commit_body, status=200)
    httpretty.register_uri(httpretty.GET, GITLINK_PULL_REQUEST_2_COMMENTS_URL,
                           body=comments_body, status=200)
    httpretty.register_uri(httpretty.GET, GITLINK_PULL_REQUEST_2_COMMITS_URL,
                           body=commit_body, status=200)


@httpretty.activate
def setup_refresh_access_token_service():
    httpretty.register_uri(httpretty.POST, GITLINK_REFRESH_TOKEN_URL, body="", status=200)




class TestGitlinkBackend(unittest.TestCase):
    """Gitlink Backend tests"""

    def test_init(self):
        """ Test for the initialization of Gitlink"""
        gitlink = Gitlink('gitlink_example', 'repo', ['aaa'], tag='')
        self.assertEqual(gitlink.owner, 'gitlink_example')
        self.assertEqual(gitlink.repository, 'repo')
        self.assertEqual(gitlink.origin, 'https://www.gitlink.org.cn/gitlink_example/repo')
        self.assertEqual(gitlink.tag, 'https://www.gitlink.org.cn/gitlink_example/repo')

    @httpretty.activate
    def test_fetch_empty(self):
        """ Test when get a empty issues API call """
        setup_gitlink_issue_services()
        empty_issue = read_file("data/gitlink//gitlink_empty_issue")
        httpretty.register_uri(httpretty.GET, GITLINK_ISSUES_URL,
                               body=empty_issue, status=200,
                               )

        from_date = datetime.datetime(2019, 1, 1)
        gitlink = Gitlink("gitlink_example", "repo", ["aaa"])

        issues = [issues for issues in gitlink.fetch(from_date=from_date, to_date=None)]

        self.assertEqual(len(issues), 0)

    @httpretty.activate
    def test_fetch_issues(self):
        setup_gitlink_issue_services()
        from_date = datetime.datetime(2019, 1, 1)
        gitlink = Gitlink("gitlink_example", "repo", ["aaa"])
        issues = [issues for issues in gitlink.fetch(from_date=from_date)]

        self.assertEqual(len(issues), 1)
        issue1 = issues[0]
        self.assertEqual(issue1['subject'], 'occaecat Lorem irure aliqua32131231')
        self.assertEqual(issue1['uuid'], 'eec26ce041167b2b93368d75f0a78faae7b31c78')
        self.assertEqual(issue1['updated_at'], "2023-02-10 11:08")
        self.assertEqual(issue1['autho']["login"], 'yystopf')
        # TODO to add collaborators information
        self.assertEqual(len(issue1['data']['comments_data']), 1)
        self.assertEqual(issue1['data']['comments_data'][0]['user_data']['login'], 'willemjiang')

    @httpretty.activate
    def test_fetch_issues_with_to_data(self):
        setup_gitlink_issue_services()
        from_date = datetime.datetime(2019, 1, 1)
        gitlink = Gitlink("gitlink_example", "repo", ["aaa"])
        issues = [issues for issues in gitlink.fetch(from_date=from_date)]

        self.assertEqual(len(issues), 1)
        issue1 = issues[0]
        self.assertEqual(issue1['subject'], 'occaecat Lorem irure aliqua32131231')
        self.assertEqual(issue1['uuid'], 'eec26ce041167b2b93368d75f0a78faae7b31c78')
        self.assertEqual(issue1['updated_at'], "2023-02-10 11:08")
        self.assertEqual(issue1['autho']["login"], 'yystopf')
        # TODO to add collaborators information
        self.assertEqual(len(issue1['data']['comments_data']), 1)
        self.assertEqual(issue1['data']['comments_data'][0]['user_data']['login'], 'willemjiang')


    @httpretty.activate
    def test_fetch_repo(self):
        setup_gitlink_basic_services()
        gitlink = Gitlink("gitlink_example", "repo", "[aaa]")
        repos = [repo for repo in gitlink.fetch(category=CATEGORY_REPO)]
        self.assertEqual(len(repos), 1)
        repo = repos[0]
        self.assertEqual(repo['repo_id'], 1402604)
        self.assertEqual(repo['name'], "矽璓工业物联操作系统XiUOS")
        self.assertEqual(repo['forks_count'], 1)
        self.assertEqual(repo['forked_count'], 236)
        self.assertEqual(repo['watchers_count'], 58)
        self.assertEqual(repo['issues_count'], 58)

    @httpretty.activate
    def test_fetch_pulls(self):
        setup_gitlink_pull_request_services()
        from_date = datetime.datetime(2019, 1, 1)
        gitlink = Gitlink("gitlink_example", "repo", "[aaa]")
        pulls = [pr for pr in gitlink.fetch(category=CATEGORY_PULL_REQUEST, from_date=from_date)]

        self.assertEqual(len(pulls), 2)
        pull = pulls[0]
        self.assertEqual(pull['id'], 12)
        self.assertEqual(pull["is_original"], False)
        self.assertEqual(pull['journals_count'], 0)
        self.assertEqual(len(pull['data']['assignees_data']), 1)
        self.assertEqual(pull['data']['assignees_data'][0]['login'], "willemjiang")
        # check if the  testers_data there
        self.assertTrue('tester_data' not in pull['data'])
        self.assertEqual(pull['data']['commits_data'], ['8cd1bca4f2989ac2e2753a152c8c4c8e065b22f5'])
        self.assertEqual(pull['data']['merged_by'], "willemjiang")
        self.assertEqual(pull['data']['merged_by_data']['login'], "willemjiang")

        pull = pulls[1]
        self.assertEqual(pull['updated_on'], 1585976439.0)
        self.assertEqual(pull['uuid'], '46df79e68e92005db5c1897844e3a0c3acf1aa4f')
        self.assertEqual(pull['data']['head']['repo']['path'], "camel-on-cloud")
        self.assertEqual(pull['data']['base']['repo']['path'], "camel-on-cloud")
        self.assertEqual(pull['data']['number'], 2)
        self.assertEqual(len(pull['data']['review_comments_data']), 1)
        self.assertEqual(pull['data']['review_comments_data'][0]['body'], "Added comment here.")
        self.assertEqual(len(pull['data']['assignees_data']), 1)
        self.assertEqual(pull['data']['assignees_data'][0]['login'], "willemjiang")
        # check if the  testers_data there
        self.assertTrue('tester_data' not in pull['data'])
        self.assertEqual(pull['data']['commits_data'], ['586cc8e511097f5c5b7a4ce803a5efcaed99b9c2'])
        self.assertEqual(pull['data']['merged_by'], None)
        self.assertEqual(pull['data']['merged_by_data'], [])

    @httpretty.activate
    def test_fetch_pulls_with_empty_commits_and_comments(self):
        from_date = datetime.datetime(2019, 1, 1)
        gitlink = Gitlink("gitlink_example", "repo", "[aaa]")
        pulls = [pr for pr in gitlink.fetch(category=CATEGORY_PULL_REQUEST, from_date=from_date)]

        self.assertEqual(len(pulls), 2)
        pull = pulls[0]
        self.assertEqual(len(pull['data']['review_comments_data']), 0)
        # check if the  testers_data there
        self.assertTrue('tester_data' not in pull['data'])
        self.assertEqual(pull['data']['commits_data'], [])
        self.assertEqual(pull['data']['merged_by'], "willemjiang")
        self.assertEqual(pull['data']['merged_by_data']['login'], "willemjiang")

        pull = pulls[1]
        self.assertEqual(len(pull['data']['review_comments_data']), 0)
        self.assertEqual(len(pull['data']['review_comments_data']), 0)
        # check if the  testers_data there
        self.assertTrue('tester_data' not in pull['data'])
        self.assertEqual(pull['data']['commits_data'], [])
        self.assertEqual(pull['data']['merged_by'], None)
        self.assertEqual(pull['data']['merged_by_data'], [])

    def test_has_resuming(self):
        """Test if it returns True when has_resuming is called"""

        self.assertEqual(Gitlink.has_resuming(), True)

    def test_has_archiving(self):
        """Test if it returns True when has_archiving is called"""

        self.assertEqual(Gitlink.has_archiving(), True)

class TestGitlinkBackendArchive(TestCaseBackendArchive):
    """Gitlink backend tests using an archive"""

    def setUp(self):
        super().setUp()
        self.backend_write_archive = Gitlink("gitee_example", "repo", ["aaa"], archive=self.archive)
        self.backend_read_archive = Gitlink("gitee_example", "repo", ["aaa"], archive=self.archive)

    @httpretty.activate
    def test_fetch_issues_from_archive(self):
        """Test whether a list of issues is returned from archive"""
        setup_gitlink_issue_services()
        self._test_fetch_from_archive(from_date=None)

    @httpretty.activate
    def test_fetch_pulls_from_archive(self):
        """Test whether a list of pull requests is returned from archive"""
        setup_gitlink_pull_request_services()
        self._test_fetch_from_archive(category=CATEGORY_PULL_REQUEST, from_date=None)

    @httpretty.activate
    def test_fetch_from_date_from_archive(self):
        """Test whether a list of issues is returned from archive after a given date"""
        setup_gitlink_issue_services()
        from_date = datetime.datetime(2016, 3, 1)
        self._test_fetch_from_archive(from_date=from_date)

    @httpretty.activate
    def test_fetch_from_empty_archive(self):
        """Test whether no issues are returned when the archive is empty"""
        setup_gitlink_basic_services()
        empty_issue = ''
        httpretty.register_uri(httpretty.GET, GITLINK_ISSUES_URL,
                               body=empty_issue, status=200)
        self._test_fetch_from_archive()



class TestGitlinkClient(unittest.TestCase):
    "Gitlink API client tests"

    @httpretty.activate
    def test_init(self):
        """ Test for the initialization of GitlinkClient """
        # setup_refresh_access_token_service()
        client = GitlinkClient('gitlink_example', 'repo', ['aaa'])
        self.assertEqual(client.owner, 'gitlink_example')
        self.assertEqual(client.repository, 'repo')
        self.assertEqual(client.max_retries, GitlinkClient.MAX_RETRIES)
        self.assertEqual(client.sleep_time, GitlinkClient.DEFAULT_SLEEP_TIME)
        self.assertEqual(client.max_retries, GitlinkClient.MAX_RETRIES)
        self.assertEqual(client.base_url, GITLINK_API_URL2)
        self.assertTrue(client.ssl_verify)

    @httpretty.activate
    def test_fetch_empty_issue(self):
        """ Test when get a empty issues API call """
        setup_gitlink_issue_services()
        empty_issue = read_file("data/gitlink/gitlink_empty_issue")
        httpretty.register_uri(httpretty.GET, GITLINK_ISSUES_URL,
                               body=empty_issue, status=200)

        from_date = datetime.datetime(2019, 1, 1)
        gitlink = Gitlink("gitlink_example", "repo", ["aaa"])

        issues = [issues for issues in gitlink.fetch(from_date=from_date, to_date=None)]

        self.assertEqual(len(issues), 0)

    @httpretty.activate
    def test_get_issues(self):
        """Test Gitlink issues API """
        setup_refresh_access_token_service()
        issues = read_file('data/gitlink/gitlink_issue')
        httpretty.register_uri(httpretty.GET, GITLINK_ISSUES_URL,
                               body=issues, status=200)

        client = GitlinkClient("gitlink_example", "repo", ['aaa'], None)
        raw_issues = [issues for issues in client.issue(287)]
        self.assertEqual(raw_issues[0], issues)
    @httpretty.activate
    def test_issue_comments(self):
        """Test Gitlink issue comments API """
        setup_refresh_access_token_service()
        issue_comments = read_file('data/gitlink//gitlink_issue_comments')
        httpretty.register_uri(httpretty.GET, GITLINK_ISSUE_COMMENTS_URL_1,
                               body=issue_comments, status=200,
                               )

        client = GitlinkClient("gitlink_example", "repo", ['aaa'], None)
        raw_issue_comments = [comments for comments in client.issue_comments("I1DACG")]
        self.assertEqual(raw_issue_comments[0], issue_comments)
    
    @httpretty.activate
    def test_pulls(self):
        setup_refresh_access_token_service()
        pull_request = read_file('data/gitlink//gitlink_pull_requests')
        httpretty.register_uri(httpretty.GET, GITLINK_PULL_REQUEST_URL,
                               body=pull_request, status=200)
        client = GitlinkClient("gitlink_example", "repo", ['aaa'], None)
        raw_pulls = [pulls for pulls in client.pulls()]
        self.assertEqual(raw_pulls[0], pull_request)

    @httpretty.activate
    def test_repo(self):
        setup_refresh_access_token_service()
        repo = read_file('data/gitlink//gitlink_repo')
        httpretty.register_uri(httpretty.GET, GITLINK_REPO_URL, body=repo, status=200)
        client = GitlinkClient("gitlink_example", "repo", ['aaa'], None)
        raw_repo = client.repo()
        self.assertEqual(raw_repo, repo)    


    
    
class TestGitlinkCommand(unittest.TestCase):
    """GitlinkCommand unit tests"""

    def test_backend_class(self):
        """Test if the backend class is Gitlink"""

        self.assertIs(GitlinkCommand.BACKEND, Gitlink)

    def test_setup_cmd_parser(self):
        """Test if it parser object is correctly initialized"""

        parser = GitlinkCommand.setup_cmd_parser()
        self.assertIsInstance(parser, BackendCommandArgumentParser)
        self.assertEqual(parser._backend, Gitlink)

        args = ['--sleep-for-rate',
                '--min-rate-to-sleep', '1',
                '--max-retries', '5',
                '--max-items', '10',
                '--sleep-time', '10',
                '--tag', 'test', '--no-archive',
                '--api-token', 'abcdefgh', 'ijklmnop',
                '--from-date', '1970-01-01',
                '--to-date', '2100-01-01',
                'gitlink_example', 'repo']
        parsed_args = parser.parse(*args)
        self.assertEqual(parsed_args.owner, 'gitlink_example')
        self.assertEqual(parsed_args.repository, 'repo')
        self.assertTrue(parsed_args.sleep_for_rate)
        self.assertEqual(parsed_args.max_retries, 5)
        self.assertEqual(parsed_args.max_items, 10)
        self.assertEqual(parsed_args.sleep_time, 10)
        self.assertEqual(parsed_args.tag, 'test')
        self.assertEqual(parsed_args.from_date, DEFAULT_DATETIME)
        self.assertEqual(parsed_args.to_date, DEFAULT_LAST_DATETIME)
        self.assertTrue(parsed_args.no_archive)
        self.assertTrue(parsed_args.ssl_verify)
        self.assertEqual(parsed_args.api_token, ['abcdefgh', 'ijklmnop'])


if __name__ == "__main__":
    httpretty.enable()
    unittest.main(warnings='ignore')
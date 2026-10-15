"""Where the caches live. The caches stay in the session scratchpad (git-ignored, regenerable by the fetchers); derived
artifacts small enough to keep go under research/compass/lifecycle/results."""
import os
SP = os.environ.get('COMPASS_SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
THETA = f'{SP}/theta'
CHAINS_0DTE = f'{THETA}/data_full/chains'
UNDERLYING = f'{THETA}/data/underlying'
INDEX = f'{THETA}/data/index'
FETCH_CACHE = f'{THETA}/fetch_cache'
WORK = os.environ.get('LC_WORK', f'{SP}/lifecycle')          # archive partitions, job logs, large intermediates
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = f'{HERE}/results'

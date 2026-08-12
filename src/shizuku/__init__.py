import cmd
from collections.abc import Callable, Iterator, Set
from dataclasses import dataclass, replace
from random import choice
from typing import IO


@dataclass(frozen=True)
class Game[S, M]:
    get_moves: Callable[[S], Set[M | None]]
    apply_move: Callable[[M | None, S], Set[S]]
    is_end: Callable[[S], bool]
    current_player: Callable[[S], int]
    player_count: Callable[[S], int]
    parse_move: Callable[[str], M]
    format_move: Callable[[M], str]
    render: Callable[[S], str]


@dataclass(frozen=True)
class Agent[S]:
    evaluate: Callable[[S], dict[int, float] | None]
    depth: int


def evaluate_move[S, M](
    game: Game[S, M], agent: Agent[S], m: M | None, b: S
) -> dict[int, float]:
    next_boards = game.apply_move(m, b)
    scores = [evaluate_board(game, agent, next_b) for next_b in next_boards]
    return {
        i: sum(score[i] for score in scores) / len(scores)
        for i in range(1, game.player_count(b) + 1)
    }


def evaluate_board[S, M](game: Game[S, M], agent: Agent[S], b: S) -> dict[int, float]:
    score = agent.evaluate(b)
    if score is not None:
        return score
    elif agent.depth == 0:
        return dict.fromkeys(range(1, game.player_count(b) + 1), 0.0)
    else:
        current = game.current_player(b)
        next_agent = replace(agent, depth=agent.depth - 1)
        scores = [evaluate_move(game, next_agent, m, b) for m in game.get_moves(b)]
        max_score = max(v[current] for v in scores)
        best_scores = [v for v in scores if v[current] == max_score]
        return {
            i: sum(score[i] for score in best_scores) / len(best_scores)
            for i in range(1, game.player_count(b) + 1)
        }


def play_auto[S, M](game: Game[S, M], agent: Agent[S], b: S) -> M | None:
    score_table = {m: evaluate_move(game, agent, m, b) for m in game.get_moves(b)}
    current = game.current_player(b)
    max_score = max(v[current] for v in score_table.values())
    return choice([m for m, v in score_table.items() if v[current] == max_score])


class Cli[S, M](cmd.Cmd):
    prompt = "> "

    def __init__(
        self,
        game: Game[S, M],
        agent: Agent[S],
        initial: S,
        stdin: IO[str] | None = None,
        stdout: IO[str] | None = None,
    ) -> None:
        super().__init__(stdin=stdin, stdout=stdout)
        self.game = game
        self.agent = agent
        self.board = initial

    def emptyline(self) -> bool:
        return False

    def _read_line(self) -> str:
        self.stdout.write(self.prompt)
        self.stdout.flush()
        return self.stdin.readline()

    def _read_lines(self) -> Iterator[str]:
        while line := self._read_line():
            yield line.rstrip("\r\n")

    def cmdloop(self) -> None:  # type: ignore[override]
        self.stdout.write(self.game.render(self.board))
        for line in self._read_lines():
            self.onecmd(line)
            self.stdout.write(self.game.render(self.board))
            if self.game.is_end(self.board):
                break

    def _apply(self, m: M | None) -> None:
        if m in self.game.get_moves(self.board):
            self.board = choice(tuple(self.game.apply_move(m, self.board)))
        elif m is None:
            self.stdout.write("Cannot Pass\n")
        else:
            self.stdout.write(f"Cannot Move: {self.game.format_move(m)}\n")

    def do_move(self, arg: str) -> None:
        self._apply(self.game.parse_move(arg))

    def do_pass(self, arg: str) -> None:
        self._apply(None)

    def do_auto(self, arg: str) -> None:
        self._apply(play_auto(self.game, self.agent, self.board))

import io
from collections.abc import Set
from dataclasses import dataclass, replace

from shizuku import Agent, Cli, Game, evaluate_board, play_auto


@dataclass(frozen=True)
class Board:
    n: int
    current_player: int = 1


def get_moves(b: Board) -> Set[int]:
    return frozenset(range(1, min(2, b.n) + 1))


def apply_move(m: int | None, b: Board) -> Set[Board]:
    assert m is not None
    n = b.n - m
    current_player = b.current_player if n == 0 else (b.current_player % 2) + 1
    return frozenset({replace(b, n=n, current_player=current_player)})


def is_end(b: Board) -> bool:
    return b.n == 0


def evaluate_state(b: Board) -> dict[int, float] | None:
    if not is_end(b):
        return None
    return {1: -0.5, 2: 0.5} if b.current_player == 1 else {1: 0.5, 2: -0.5}


def render(b: Board) -> str:
    if is_end(b):
        return f"Player {b.current_player} loses.\n"
    return f"n={b.n}, Player {b.current_player}'s turn.\n"


NIM_GAME: Game[Board, int] = Game(
    get_moves=get_moves,
    apply_move=apply_move,
    is_end=is_end,
    current_player=lambda b: b.current_player,
    player_count=lambda b: 2,
    parse_move=int,
    format_move=str,
    render=render,
)


def test_evaluate_board_single_stone_forces_mover_to_lose():
    b = Board(n=1, current_player=1)
    assert evaluate_board(NIM_GAME, Agent(evaluate_state, 1), b) == {1: -0.5, 2: 0.5}


def test_evaluate_board_two_stones_favors_mover():
    b = Board(n=2, current_player=1)
    assert evaluate_board(NIM_GAME, Agent(evaluate_state, 2), b) == {1: 0.5, 2: -0.5}


def test_evaluate_board_three_stones_favors_mover():
    b = Board(n=3, current_player=1)
    assert evaluate_board(NIM_GAME, Agent(evaluate_state, 3), b) == {1: 0.5, 2: -0.5}


def test_play_auto_leaves_opponent_with_forced_loss():
    b = Board(n=2, current_player=1)
    assert play_auto(NIM_GAME, Agent(evaluate_state, 2), b) == 1


def check_cmdcli(input_text: str, n: int) -> str:
    stdout = io.StringIO()
    Cli(
        NIM_GAME,
        Agent(evaluate_state, n),
        Board(n),
        stdin=io.StringIO(input_text),
        stdout=stdout,
    ).cmdloop()
    return stdout.getvalue()


def test_cmdcli_move_sequence_ends_game():
    output = check_cmdcli("move 1\nmove 1\n", 2)
    assert "Cannot Move" not in output
    assert "Player 2 loses." in output


def test_cmdcli_rejects_illegal_move():
    output = check_cmdcli("move 5\nmove 1\nmove 1\n", 2)
    assert "Cannot Move: 5" in output
    assert "Player 2 loses." in output


def test_cmdcli_pass_always_fails():
    output = check_cmdcli("pass\nmove 1\nmove 1\n", 2)
    assert "Cannot Pass" in output


def test_cmdcli_auto_finishes_the_game():
    output = check_cmdcli("auto\n" * 4, 3)
    assert "Cannot Move" not in output
    assert "loses." in output

# Declare this file as a StarkNet contract and set the required
# builtins.
%lang starknet
%builtins pedersen range_check

from starkware.cairo.common.cairo_builtins import HashBuiltin

# Define a storage variable.
@storage_var
func balance() -> (res : felt):
end

@constructor
func constructor{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr
} (initial_balance : felt):
    balance.write(initial_balance)
    return ()
end

# Increases the balance by the given amount.
@external
func increase_balance{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*,
        range_check_ptr}(amount1 : felt, amount2 : felt):
    let (res) = balance.read()
    balance.write(res + amount1 + amount2)
    return ()
end

# Returns the current balance.
@view
func get_balance{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*,
        range_check_ptr}() -> (res : felt):
    let (res) = balance.read()
    return (res)
end

struct Point:
    member x : felt
    member y : felt
end

@view
func sum_point_array(points_len: felt, points: Point*) -> (res: Point):
    if points_len == 0:
        return (res=Point(x=0, y=0))
    end
    let (rest) = sum_point_array(points_len=points_len - 1, points=points + Point.SIZE)
    return (res=Point(
        x=points[0].x + rest.x,
        y=points[0].y + rest.y
    ))
end

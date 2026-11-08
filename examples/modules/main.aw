-- Module paths are rooted at this entry file's directory, not cwd or PATH.
import geometry.points as geo
import results as r
function main() -> i64
    local first: geo.Point = geo.Point(10,20)
    local next: geo.Point = geo.shifted(first,5)
    print(first.x)
    print(next.x)
    match r.make() then
        case r.Result.Value(point) then print(point.x)
        case r.Result.Empty() then print(0)
    end
    return 0
end

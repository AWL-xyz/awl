use File.aw as file;
use Plan.aw as plan;
use Process.aw as child;
func run[i64] :: source:text,timeout:i64 {
    @s tokens vector<text>:vector.new<text>(0);
    @s metadata vector<i64>:vector.new<i64>(0);
    @s ranges vector<i64>:vector.new<i64>(32);
    @s out spool:spool.new(4096);
    @s err spool:spool.new(4096);
    if not vector.valid(tokens) or not vector.valid(metadata) or not vector.valid(ranges) or not spool.valid(out) or not spool.valid(err) { return 9; };
    if not plan.parse(source,tokens,metadata,ranges) { print("invalid task plan"); return 2; };
    @p i:0;
    while i<vector.length(ranges) {
        @p start:vector.get(ranges,i); @p count:vector.get(ranges,i+1);
        print("task " + string.fromi64(i/2+1));
        spool.clear(out); spool.clear(err);
        @p args:vector.view(tokens,start+1,count-1);
        @p status:child.run(vector.get(tokens,start),args,out,err,timeout);
        if spool.bytes(out)>0 { print("stdout:"); if spool.print(out)!=0 { return 7; }; };
        if spool.bytes(err)>0 { print("stderr:"); if spool.print(err)!=0 { return 7; }; };
        match status then
            case child.Outcome.Passed() then print("passed");
            case child.Outcome.Exited(code) then print("exit " + string.fromi64(code)); return 1;
            case child.Outcome.TimedOut() then print("timeout"); return 4;
            case child.Outcome.Failed(code) then print("capture error " + string.fromi64(code)); return 5;
        end;
        i:i+2;
    };
    print("all tasks passed"); return 0;
};
func main[i64] {
    if arg.count()!=2 { print("usage: taskrun PLAN.json TIMEOUT_MS"); return 2; };
    if not arg.textvalid(0) or not arg.i64valid(1) { return 2; };
    @p timeout:arg.i64(1);
    if timeout<1 or timeout>60000 { return 2; };
    match file.read(arg.text(0)) then
        case file.Read.Text(source) then return run(source,timeout);
        case file.Read.Failed(issue) then
            match issue then
                case file.Issue.Missing() then print("missing plan"); return 3;
                case file.Issue.Io(code) then print("read error"); print(code); return 3;
                case file.Issue.TooLarge(bytes) then print("plan too large"); print(bytes); return 3;
            end;
    end;
};

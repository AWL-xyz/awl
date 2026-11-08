exports{
 @r enum Outcome
    Passed();
    Exited(code:i64);
    TimedOut();
    Failed(code:i64);
 end;
 @r func run :: program:text,args:view<text>,@b out:spool,@b err:spool,timeout:i64: Outcome {
    @p code:process_capture(program,args,out,err,timeout);
    if code==0 { return Outcome.Passed(); };
    if code>0 { return Outcome.Exited(code); };
    if code==-4 { return Outcome.TimedOut(); };
    return Outcome.Failed(code);
 };
};

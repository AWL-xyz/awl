#include "kparse.cpp"
#include <iostream>
int main(){try{
 const std::string text="func main[i64] { @s args vector<text>:vector.new<text>(0); @s out spool:spool.new(8); @s err spool:spool.new(8); print(process_capture(\"/bin/true\",vector.view(args,0,0),out,err,50)); return 0; };";
 auto seed=parse_source(text.data(),text.size());if(!seed->diagnostics.empty())return 1;Checker(*seed).run();Verifier(*seed).run();unsigned count=1;Id call=0;for(Id i=0;i<seed->arena.size();++i)if(seed->arena[i].value=="process_capture")call=i;
 for(unsigned mode=0;mode<6;++mode){Unit u=*seed;auto &n=u.arena[call];if(mode==0)n.type="unit";if(mode==1)n.children.pop_back();if(mode==2)n.value="process_shell";if(mode==3)std::swap(n.children[0],n.children[1]);if(mode==4)u.aesop_syntax=false;if(mode==5)u.arena[n.children[2]].type="string";serialize(u);auto before=u.json;bool failed=false;try{Verifier(u).run();}catch(const Failure &f){if(f.diagnostic.code!="E500")return 2;failed=true;}serialize(u);if(!failed||before!=u.json)return 3;++count;}
 std::cout<<"PASS "<<count<<" independent process verifier cases\n";return 0;
}catch(const Failure &f){std::cerr<<f.diagnostic.message<<'\n';return 1;}}

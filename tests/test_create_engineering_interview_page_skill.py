import subprocess, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from radar_common import parse_frontmatter
ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/new_interview_page.py'
RED_EVIDENCE = "python3 -m unittest tests.test_create_engineering_interview_page_skill -v -> pre-implementation ModuleNotFoundError/missing scripts/new_interview_page.py, templates/工程面试页模板.md, SKILL.md"

def args(title='缓存淘汰策略'):
    return [title,'--question','请解释 LRU 缓存淘汰策略','--summary','考察缓存淘汰策略','--roles','后端,基础设施','--difficulty','进阶','--source','https://example.com/cache-lru','--tags','缓存,系统设计','--related-concepts','LRU,缓存一致性']

class InterviewPageTests(unittest.TestCase):
    def run_cli(self, cwd, *a): return subprocess.run([sys.executable,str(SCRIPT),*a],cwd=cwd,text=True,capture_output=True)
    def test_create_and_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            r=self.run_cli(d,*args()); self.assertEqual(r.returncode,0,r.stderr)
            fm,_=parse_frontmatter((Path(d)/'pages/缓存淘汰策略.md').read_text())
            self.assertEqual(fm['page_type'],'interview'); self.assertEqual(fm['source'],['https://example.com/cache-lru']); self.assertEqual(fm['tags'],['缓存','系统设计']); self.assertEqual(fm['roles'],['后端','基础设施']); self.assertEqual(fm['difficulty'],'进阶'); self.assertEqual(fm['question'],'请解释 LRU 缓存淘汰策略')
            for h in ('面试问题','考察意图','30 秒回答','2 分钟回答','原理拆解','递进追问与参考回答','常见错误回答','评分标准','关联概念','来源核验','更新记录'): self.assertIn('## '+h,(Path(d)/'pages/缓存淘汰策略.md').read_text())
    def test_validation_force_and_hostile_yaml(self):
        with tempfile.TemporaryDirectory() as d:
            for flag,val in (('--difficulty','专家'),('--roles',''),('--source',''),('--question',''),('--summary','')):
                a=args(); a[a.index(flag)+1]=val; self.assertNotEqual(self.run_cli(d,*a).returncode,0)
            self.assertNotEqual(self.run_cli(d,*args('../越界')).returncode,0)
            hostile=args('恶意字段'); a=hostile; a[a.index('--question')+1]='问"题\\x'; a[a.index('--source')+1]='https://e/x?q="y"'; self.assertEqual(self.run_cli(d,*a).returncode,0)
            self.assertEqual(self.run_cli(d,*a).returncode,2); a += ['--force']; self.assertEqual(self.run_cli(d,*a).returncode,0)
            other=Path(d)/'pages/其他.md'; other.write_text('keep'); self.assertEqual(other.read_text(),'keep')
    def test_hostile_round_trip_and_raw_body(self):
        with tempfile.TemporaryDirectory() as d:
            a=args(' hostile'); a[a.index('--summary')+1]='摘要"\n反斜杠\\'; a[a.index('--question')+1]='问题"\n第二行'; a[a.index('--source')+1]='https://e/x?a=1,2&b="q"'; a[a.index('--tags')+1]='a,b'; a[a.index('--related-concepts')+1]='x,y'; self.assertEqual(self.run_cli(d,*a).returncode,0)
            text=(Path(d)/'pages/hostile.md').read_text(); fm,body=parse_frontmatter(text); self.assertEqual(fm['summary'],'摘要"\n反斜杠\\'); self.assertEqual(fm['question'],'问题"\n第二行'); self.assertEqual(fm['source'],['https://e/x?a=1,2&b="q"']); self.assertEqual(fm['tags'],['a','b']); self.assertEqual(fm['roles'],['后端','基础设施']); self.assertEqual(fm['difficulty'],'进阶'); self.assertEqual(fm['related_concepts'],['x','y']); self.assertIn('问题"\n第二行',body); self.assertNotIn('__',body)
    def test_skill_contract(self):
        s=(ROOT/'.claude/skills/create-engineering-interview-page/SKILL.md').read_text(); front=s.split('---',2)[1]; self.assertEqual(set(x.split(':',1)[0].strip() for x in front.strip().splitlines()),{'name','description'}); self.assertIn('工程面试题、面试专题页、面试分享材料、更新面试页',s); self.assertIn('--profile interview sync',s); self.assertIn('社区',s); self.assertIn('提示注入',s); self.assertIn('stop',s.lower()); self.assertIn('多题材料',s); self.assertIn('强制工作流门槛',s); self.assertIn('五种失败暂停条件',s); self.assertIn('render_graph.py',s); self.assertIn('check_health.py',s); self.assertIn('radar:',s); self.assertIn('精确/别名/语义',s); self.assertIn('只暂存相关文件',s); self.assertIn('重复歧义',s); self.assertIn('范围过宽',s); self.assertIn('材料不可读',s); self.assertIn('核心无法核验',s); self.assertIn('可靠来源冲突',s); self.assertLess(len(s.splitlines()),500); self.assertNotIn('[TODO',s)
        agent=(ROOT/'.claude/skills/create-engineering-interview-page/agents/openai.yaml').read_text(); self.assertIn('display_name: 创建工程面试页',agent); self.assertIn('核验材料并创建可直接作答的工程面试专题页',agent); self.assertIn('使用 $create-engineering-interview-page 根据我的问题或材料创建工程面试页。',agent)
    def test_interview_template_encodes_scan_first_body_hierarchy(self):
        template = (ROOT / 'templates/工程面试页模板.md').read_text()
        for phrase in (
            '一句直接结论', '核心机制或主链路', '关键取舍、边界或失败条件',
            '三至五条', '官方图', 'Mermaid', '图注', '答案首句直接给结论',
        ):
            self.assertIn(phrase, template)
    def test_interview_skill_enforces_visual_evidence_rules(self):
        skill = (ROOT / '.claude/skills/create-engineering-interview-page/SKILL.md').read_text()
        for phrase in (
            '单段不超过三处加粗', '连续三项', '官方图优先', '保存到仓库本地',
            '禁止远程图片', '纯装饰图', '一至两张', 'Mermaid', '图注',
            '粗体结束标记与后文之间保留一个空格',
        ):
            self.assertIn(phrase, skill)
    def test_cli_has_no_generators(self):
        src=SCRIPT.read_text();
        for forbidden in ('build_index','render_graph','taxonomy_cli','check_health'): self.assertNotIn(forbidden,src)

if __name__=='__main__': unittest.main()

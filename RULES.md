gate: cmd=make.check & order=[yapf_diff,docformatter_check,ruff,mypy,basedpyright,pydoclint,bandit_medium,pytest,coverage_100] & path_filters=absent & editor=vscode_same
verify: runner=make & custom_cmd=absent

a1: core=[utils.py,location.py] & utils=[auto_import,modulecontent] & other=module
a2c: kind=content -> isolated & reach=registry.methode_call & imported=off
a2s: kind=system -> vital & broken=crash & imports_allowed=system_only
a3: kind=content -> import_content=absent
a4: collab=registry.methode_call(methodes) & direct_import=absent
a5: path=modules/tier/store/facet/aisle.py & tier=[system,content] & facet=[api,mcp,methodes,tasks] & class=store_aisle_facet_pascal
a6: store_dirs=[api,mcp,methodes,tasks,internal,libs,tests] & extra_dirs=absent
a7: dir=internal -> private & importers=[own_methodes,own_tasks] & controller_import=absent & cross_module=absent
a8: kind=system -> impl=libs & surface=init.__all__ & outside_import=package(modules.system.name) & libs_import=absent & relative=inside_only
a9: names=[store,aisle,facet] -> case=lower_snake_case
a10: init=[__api__,__mcp__,__methodes__,__tasks__] & names=resolve
a_by: tests=[core/tests/test_layout.py,modules/system/registry/libs/tests/test_isolation.py,tests/test_contract.py]

b11: classes_per_file<=1 & companion[protocol,exception,enum]=own_file & facet_file=aisle_class
b12: base=[api:apiroute,mcp:mcproute,methodes:methodesroute,tasks:tasksroute]
b13: class=pascalcase & suffix=[api,mcp,methodes,tasks]
b14: markers=[api:get/post/put/delete/patch,mcp:tool/resource,methodes:methode,tasks:bounded/continuous]
b15: marked_handler=async
b16: ticket=#1042 & worker=[route.bounded,route.continuous] & start_stop=lifespan_cooperative & on_demand=absent & tasksroute.invoke=raises & route.task=removed & ref=[b53,p]
b_by: tests=[modules/system/route/libs/tests/test_facet_contract.py,core/tests/test_hygiene.py(b11)]
b11_split: files=[registry.py,methode.py,route.py,declarations.py,dependencies.py,location.py,utils.py] -> one_class_files & colocated_test=each

c17: handler=marked(api,mcp,methodes,tasks) -> first=with_self.declarations & block_missing=unplug & crash=absent
c18: methode_call(x.y.z) -> declare(x.y.z)=same_handler & called<=declared & broken_dep=cascade_unplug
c19: sibling_marked_call=methode_call & self_call=[unmarked_same_file_helper,internal_import]
c20: cross_module_call=result & raise=absent & registry=catch_wrap
c_by: test=modules/system/declarations/libs/tests/test_call_contract.py

d21: free_functions=absent & helpers=staticmethod & tests=exempt
d22: masking=absent & tokens=[type_ignore,pyright_ignore,noqa,nosec,cast(]:absent & disabled_report_rules=absent
d23: print(=absent & logging=logs_module
d24: coercion=[str(,int(,bool(,float(] -> level=warning
d25: bandit.severity_level=medium & findings>=medium:absent
d_by: tests=core/tests/test_hygiene.py(masking,print,free_functions,casts) & gate=bandit

e26: any=absent(written,inferred) & annotate=[variable,param,return] & tools=[basedpyright_strict,reportany,reportexplicitany,mypy,ruff_ann]
e26b: annotation=object -> allowed=dynamic_dispatch_core_only & field=one_concrete_type & nullable=x|null:ok & union=str_int:smell & fix=typed_model
e26b_allow: file=tests/enforcement/typing.py & narrow=model.model_validate(value) & fresh_object=absent
e27: scope=[module,class,function] -> docstring=google & tool=pydoclint & parts=[summary,args,returns,raises]
e28: pep695_type_alias=absent & use=plain_assignment
e_by: gate=[basedpyright,mypy,ruff_ann,pydoclint] & script=scripts/style.py(object) & tests=[core/tests/test_typing.py,tests/enforcement/typing.py]

f29: depth<=2 & openers=[for,branch,while,with,try,comprehension,multiline_list,multiline_tuple,multiline_dict,multiline_call] & class_def=0 & depth3=extract_helper|cheaper_algorithm
f30: comprehension_for<=1
f31: multiline_block(f29_openers) & neighbour_in_suite -> blank_line=before_after & def_class=exempt
f_by: tests=[core/tests/test_nesting.py(f29,f30),core/tests/test_spacing.py(f31)]

g32: line<=80
g33: elements>=2 -> one_per_line & magic_trailing_comma & closing=dedented
g34: bracket -> newline & indent=1_tab & closing=dedented_own_line & align_to_bracket=absent
g35: imports=isort(ruff_i) & first_group=[core,modules]
g36: docformatter(description_wrap=80,summary_wrap=absent)
g_by: gate=[yapf_diff,docformatter_check,ruff_i]

h37: coverage=100(line,branch) & scope=[global,per_file]
h38: code_change -> tests=same_change
h39: dirs=[api,mcp,methodes,tasks,libs,internal,core] -> tests_dir=own & file=test_source.py_1_per_source & global=top_level_tests
h40: marker=integration-only & use=[lifespan,supervisor_loop,workers] & unit_gate=excluded & docker_integration_gate=mandatory & unit_testable_code=absent
h40b: mock=absent & fake=absent & stub=absent & double=absent & external_app -> container=throwaway & test=pytest.mark.integration & gate=make.integration & teardown=even_on_failure
h_by: gate=[pytest,scripts/check_coverage.py_100] & test=core/tests/test_hygiene.py(h39)

i41: verify=make(check,gate) & custom_cmd=absent
i42: commits=atomic & ai_attribution=absent & coauthored_by=absent & generated_with=absent & author=pikatsuto
i43: make.clean -> removes=[venv,caches,coverage,pyc]
i44: code_lang=english(comments,docstrings,yaml) & user_lang=french

j45: with_self.declarations & modes=2 & enter=declaration_pass(body=skipped) & call=body_after_pass & ast=absent & foreign_import=absent
j46: methodes=runtime_enum & case=insensitive & identity=store.aisle.methode(uppercase,generated)
j47: with=implicit_try_except & broken=unplug_self(tools,api) & cascade=fixed_point_declarers & module_broken=partial(affected_only) & system_broken=program_killed
j48: dependency=binary_declaration_driven & reachable(loader,live_reload) & unreachable=unplug_declarers & graph=absent & tier_engine=absent

k49: port=5000 & serves=[api,mcp] & micro_proxy=internal & port_5001=removed & process=1 & thread=1 & singletons=shared
k50: url=/api,mcp/v1/store/aisle/function/ & mcp_tool=store_aisle_function
k51: tools=hidden_until_discovered & reveal=[tools,api] & reveal_default=off & api=public_internet_security
k52: live_reload=exec_root & broken_edit=logged_ignored & last_valid=serving & gitflow=model_a & main=served_validated & feature=branch_worktree & dir=.worktrees(gitignored)
k53: lifespan=[mount_mcp,start_workers,resolver,system_kill] & shutdown=stop_signal_all -> wait_all_concurrently(each<=grace) -> cancel_after_grace(warning) & cancel_unasked=absent
k54: module=discovery & rayons=[tools,api,methodes,rag] & known_in_advance=[routes,capabilities] & api_doc_tool=stub(patented_backend)

l55: db=postgresql(durable) & cache=redis(volatile,coordination) & sqlite=absent & orm=sqlalchemy2_async & tables=per_module
l55a: modules=[postgres,redis] -> pure_library(libs,facet=absent) & postgres=[base,engine] & redis=typed_async_client & import=package_surface
l55b: tables=model & class=declarative(base) & file_per_class & single=model.py & several=model/(init_reexport_absolute_imports) & queries=native_orm_session
l55c: migrations=alembic_async & dir=repo_root & env.py=imports_all_models & target=base.metadata & apply=make.migrate
l55d: real_connection_code -> marker=integration-only & tests=pytest.mark.integration & run=make.integration
l56: lang=python_only & deps=few & core=thin_auto_discovery & frontend=astro_ssr
jkl_by: families=[j,k,l] & proof=[tests/test_contract.py,docker_integration_gate] & static_lint=absent

m57: enforcement=owner_distributed & owner=holds[test,scripts/style.py_hook] & central_test=absent & tests/test_architecture.py=absent
m57a: owners=[registry:test_isolation.py,route:test_facet_contract.py,declarations:test_call_contract.py,core:core/tests/test_files.py(layout,hygiene,nesting,spacing)] & global=tests/test_contract.py

n_bar: scope=frontend & bar=backend_same & gate=make.check_same_order & guard=absent & exemption=absent
n58: runtime=bun_1.4.2 & order=[prettier_check,eslint_max_warnings_0,astro_check,tsc_noemit,vitest_coverage_100] & covers=[make.format,make.docs,make.clean,make.gate] & integration=make.front-e2e
n59: path=src/modules/kebab-name/ & files=[module.ts:req,page.astro:req,layout.astro,loading.astro,error.astro,segment.[param].astro] & dirs=[_components(.astro),_islands(.tsx),_lib(.ts)] & ext=own_only & shared=src/shared/name/index.ts
n60: module.ts=[route,label,menu,icon,order,consumes] & menu=true -> left_rail & route=derived_from_dir & manifest=checked_vs_fs
n61: module_import_module=absent & share=[@shared/all,backend_api] & shared_reach=surface(@shared/logs) & inner_file=absent
n62: ts=one_class & free_function=absent & helpers=static(d21) & tsx=one_component(class=absent) & exempt=[types.ts(types_only),index.ts(reexport_only)](test=absent)
n62a: dir=src/shared/components/ui/ & count=exempt & eslint_hard_rules=apply
n63: js=islands_only(_islands,client_directive) & static=astro & personalised=server:defer
n64: colors=src/shared/tokens/ & raw=[#hex,rgb(,hsl(]:gate_fail & banned_fonts=[inter,roboto,system-ui,helvetica,arial]:gate_fail & ref=frontend/design.md
n65: masking=absent & rejected=[@ts-ignore,@ts-expect-error,eslint-disable,as_any,nonnull_bang] & any=absent & return_type=explicit & jsdoc=all_symbols & console=@shared/logs_only & cols<=80 & depth<=2
n66: tests=colocated & file=source.test.ts(x) & coverage=100(lines,branches,functions,statements,per_file) & astro=unit_exempt(playwright) & marker=v8_ignore_start_integration-only(e2e_assertion)
n67: gate=make.e2e & real_ssr_bundle & viewports=[desktop,mobile] & asserts=[module_answers_route,rail,axe_violations=0,page_js<=islands_bundles] & shared_header=#1011
n67a: e2e=ci(make.integration) & commit_hook=[lint,coverage_100_staged_files] & heavy=forgejo_runner(push=[develop,main],pull_request) & local=make.check-all
n68: eslint_rules_off=frozen(enforcement/gate.ts) & each=justifying_rule & other_off=gate_fail_until_declared
n69: marker=v8_ignore_start_integration-only -> reason=stated & e2e_spec_matches=file & else=gate_fail & test=enforcement/backed.ts
n70: one_class&free_function=count_every_top_level_declaration(exported|private,const_arrow=free_function) & scope=[src,integrations,scripts]
n71: rule=g33 & tool=frontend/scripts/style.ts & runs=after_prettier & canonical=signature.open(prettier(source)) & tests=exempt
n72: rule=f29 & counts=every_opener & test=enforcement/nesting.ts & eslint=[max-depth,max-nested-callbacks,complexity,sonarjs/cognitive-complexity] & scope_exempt=[config_files,test_suites,src/shared/components/ui/]
n73: type-coverage_strict=100 & any=absent(written,inferred,tests_included) & knip=clean[dead_file,dead_export,unused_dep,missing_dep]
n74: .vscode/settings.json=pins[flat_eslint_config,prettier,workspace_tsdk,ruler_80]
n75: make.build=deployable_artefacts & make.start=build_serve(ssr_bundle,node_adapter) & dev_server=absent & preview_server=absent
n76: contract=src/shared/contracts/view/[json_fixtures,ts_shapes,guard] & fixture_importer=own_colocated_test_only & test=enforcement/fixtures.ts
n80: console=gabriel-guillou.fr/cunegonde & links_assets_fetch=url.of(@shared/url) & root_relative_literal=[href,src,action,fetch]:gate_fail & api=@shared/api(literal_path_ok) & test=enforcement/base-path.ts
n81: shared=infra_only & ui_component(.astro,.tsx)_in_shared=gate_fail & test=enforcement/scope.ts & exception=@shared/registry/unavailable.astro & infra=[shared/tokens,shared/icons]
n82: collab=[registry.component(module.name),registry.call(module.name)] & import=absent & id=compile_time_key(module.ts) & free_string=absent
n82a: manifest.consumes=every_called_id(front,back_for_impact_map) & unlisted_call=gate_fail & test=enforcement/consumes.ts
n82b: resolve=async_always & provider_missing|throwing|rejecting=undefined(logged) & consumer_undefined=degraded(@shared/registry/unavailable.astro) & crash=absent
n83: styling=tailwind_only & content_module_style=absent & tokens(@theme)=utilities[colors,radii,fonts,--fs-scale,--spacing-console-content]
n83a: view=[tailwind_classes,theme_registry_capabilities] & scoped_style=absent & own_css=absent & test=enforcement/style.ts & exception=theme_owns(shared/tokens/components.css)
n83b: prop=numeric|enum(stack.gap,grid.columns) -> class_via=fixed_enumerated_map & runtime_string=absent & plain_object=absent(eslint_security/detect-object-injection)
n_by: tests=[frontend/eslint.config.ts,frontend/tsconfig.json,frontend/vitest.config.ts,frontend/e2e/console.spec.ts(n67)] & dir=frontend/src/shared/enforcement/ & classes=[layout(n59),manifest(n60),isolation(n61),structure(n62,n70),hygiene(n64),gate(n68),backed(n69),signature(n71),nesting(n72),fixtures(n76),basepath(n80),scope(n81),consumes(n82),style(n83)] & colocated_test=each

o_bound: module=browser & ticket=#972 & purpose=audit_own_apps & others_captcha=absent
o76: audit_run=declared_perimeter_only & file=config/captcha-audit-scope.toml(flat_keys=[bench,owned],versioned) & reader=auditscope.load() & env_widening=absent & declaration=[missing,unreadable,malformed] -> perimeter=empty(fail_closed) & test=browser/internal/tests/test_audit_scope.py
o77: gate=fail_closed & pass=[scheme(http,https),url_host,host_in_perimeter,budget_ok] & budget=solvebudget(min_interval_per_host,ceiling_per_rolling_hour) & journal=every_decision(host,reason) & refused_charged=absent & door=captchagate(browser/internal/captcha_gate.py) & tests=[browser/internal/tests/test_captcha_gate.py,browser/internal/tests/test_solve_budget.py]
o78: captcha_farm_reference=absent(source,setup.cfg,pyproject.toml,frontend/package.json) & enforced=test_fails_make.gate & test_deletion=blocked & test=browser/tests/test_solver_farm_ban.py
o79: o_rules=own_test(m) & central_test_captcha_audit.py=absent & test=beside_constrained_class

p_intro: interrupt=cooperative_only & bare_cancel=absent & kill=at_least_once(replay=unit_in_flight,capture=after_every_unit) & graceful_stop=exactly_once
p80: marker=chosen & default=absent & bounded=route.bounded(grace=s,sig=(self)->void) & continuous=route.continuous(grace=s,sig=(self,run:taskrun)->void,run.state=taskcheckpoint) & route.task=gone & test=route/libs/tests/test_task_interruption.py
p81: continuous -> c1=one_param_after_self(taskrun) & c2=while_tests(run.stopping) & constant_truthy_while=absent & c3=awaits(run.capture) & c4=sleep(=absent(use=await_run.wait) & c5=grace_literal
p82: bounded -> b1=params=[self] & b2=constant_truthy_while=absent & test=same
p83: grace=numeric_literal(0,route.grace_max=10.0s] & ids=[c5,b3] & route.bounded|route.continuous_out_of_range=raises_valueerror & tests=[route/libs/tests/test_task_interruption.py,route/libs/tests/test_route.py]
p84: owner=route & logic=tests/enforcement/interruption.py & sweep=route/libs/tests/test_task_interruption.py(negative_control_per_rule) & reuse=scripts/style.py(run_check)
p85: state=durable & instances=1 & module=workers & table=workers_task_state & start=after(pg_try_advisory_lock,autocommit_conn) & lock_freed=process_death & lease=absent & heartbeat=absent
p85a: lock_held_elsewhere -> started=off
p85b: saved_state=invalid -> refused_loud(taskstateerror,logged) & worker=stopped & row=untouched & silent_reset=absent
p85c: locks_released=after_drain & tests=[workers/libs/tests/test_task_store_integration.py,workers/libs/tests/test_task_lock_integration.py,workers/libs/tests/test_task_runner_integration.py,proxy/libs/tests/test_lifespan_integration.py]

/-
  MEXT の Lean 検査器の健全性（Mathlib を使わない。Lean 4 の標準のライブラリだけで検査できる）

  mext の `lean` コマンドは、各 Extension E について、次を出力する（優先順位があれば、preferred の検査 checkPref も）。
  - 証明書による方式:
      theorem : Mext.checkCert T E cert = true := by decide +kernel
    cert は mext が書き出す E の導出の列である。checkCert は、E が無矛盾であること、E が W を含み
    規則と「正当化が E と無矛盾なデフォルト」とで閉じていること、cert の各段を W から順に使うと
    E が得られることを Bool で確かめる。
  0.5 までの `mext lean` は、Γ を計算し直す方式を出力していた（例に保存してある .lean はこの方式で、それぞれ単独で検査できる）:
      theorem : Mext.isExtension T E = true := by decide +kernel
    isExtension は Γ(E) を有限回の反復（規則の数 + デフォルトの数 + 1 回）で計算し、E と比べる。

  このファイルは、どちらの Bool の判定も（preferred の判定 checkPref も）、Reiter の Extension の Prop としての定義
  （E は無矛盾で、W を含み、規則と「正当化が E と無矛盾なデフォルト」とで閉じた最小の集合である）
  を導くこと（健全性: checkCert_sound、isExtension_sound、checkPref_sound）を示す。

  定義（Dflt, Theory, subsetL, consistentL, okDefaults,
  Step, stepConcl, runCert, closedB, checkCert, genB, rivalB, blockedB, runPref, dfltIdx, transClosedB, checkPref）は、
  mext/core.py の LEAN_PRELUDE と同じでなければならない（tests/run_tool_tests.py が確かめる）。
  sameSet, step, iter, gamma, isExtension と isExtension_sound は 0.5 までの出力の検査器で、記録として残してある。
  preferred の仕様（Higher, RuleDerivable, Generating, Rival, conclOf, PreferredGen）と健全性定理 checkPref_sound は
  このファイルにだけある。
-/
namespace Mext

structure Dflt where
  pre : List Int
  just : List Int
  concl : List Int
deriving Repr

structure Theory where
  W : List Int
  rules : List (List Int × Int)
  defaults : List Dflt

def subsetL (a b : List Int) : Bool := a.all (fun x => b.contains x)

def sameSet (a b : List Int) : Bool := subsetL a b && subsetL b a

def consistentL (S : List Int) : Bool := S.all (fun x => !S.contains (-x))

/-- E に照らして正当化が無矛盾なデフォルト -/
def okDefaults (T : Theory) (E : List Int) : List Dflt :=
  T.defaults.filter (fun d => d.just.all (fun j => !E.contains (-j)))

/-- 1 ステップ: 規則と（前提が満たされた）デフォルトの結論を加える -/
def step (T : Theory) (ds : List Dflt) (S : List Int) : List Int :=
  let fromRules := (T.rules.filter (fun r => subsetL r.1 S)).map (fun r => r.2)
  let fromDefs := ((ds.filter (fun d => subsetL d.pre S)).map (fun d => d.concl)).flatten
  (S ++ fromRules ++ fromDefs).eraseDups

def iter (T : Theory) (ds : List Dflt) : Nat → List Int → List Int
  | 0, S => S
  | n + 1, S => iter T ds n (step T ds S)

/-- Γ(E)（反復回数は規則とデフォルトの数 + 1 で十分） -/
def gamma (T : Theory) (E : List Int) : List Int :=
  iter T (okDefaults T E) (T.rules.length + T.defaults.length + 1) T.W

/-- E は Extension か（無矛盾で、Γ(E) = E） -/
def isExtension (T : Theory) (E : List Int) : Bool :=
  consistentL E && sameSet (gamma T E) E

/-! ## Prop としての仕様 -/

/-- S は W を含み、規則とデフォルトの組 ds で閉じている -/
def Closed (T : Theory) (ds : List Dflt) (S : List Int) : Prop :=
  (∀ x ∈ T.W, x ∈ S) ∧
  (∀ r ∈ T.rules, (∀ x ∈ r.1, x ∈ S) → r.2 ∈ S) ∧
  (∀ d ∈ ds, (∀ x ∈ d.pre, x ∈ S) → ∀ c ∈ d.concl, c ∈ S)

/-- Reiter の Extension（リテラル型・無矛盾なもの）:
    E は無矛盾で、E 自身が「W を含み、規則と E に照らして働くデフォルトで閉じた」集合であり、
    しかもそのような集合のうち最小である（つまり E = Γ(E)）。 -/
def ReiterExtension (T : Theory) (E : List Int) : Prop :=
  (∀ x ∈ E, -x ∉ E) ∧
  Closed T (okDefaults T E) E ∧
  (∀ S, Closed T (okDefaults T E) S → ∀ x ∈ E, x ∈ S)


/-! ### 補題 -/

theorem subsetL_iff (a b : List Int) : subsetL a b = true ↔ ∀ x ∈ a, x ∈ b := by
  simp [subsetL]

theorem iter_succ (T : Theory) (ds : List Dflt) (n : Nat) :
    ∀ S, iter T ds (n+1) S = step T ds (iter T ds n S) := by
  induction n with
  | zero => intro S; simp [iter]
  | succ n ih => intro S; rw [iter, ih (step T ds S)]; rfl

theorem step_mem (T : Theory) (ds : List Dflt) (S : List Int) (x : Int) :
    x ∈ step T ds S ↔ x ∈ S ∨ (∃ r ∈ T.rules, (∀ y ∈ r.1, y ∈ S) ∧ r.2 = x) ∨
      (∃ d ∈ ds, (∀ y ∈ d.pre, y ∈ S) ∧ x ∈ d.concl) := by
  simp only [step, List.mem_eraseDups, List.mem_append, List.mem_map, List.mem_filter,
    List.mem_flatten, subsetL_iff]
  constructor
  · rintro ((h | ⟨r, ⟨hr, hb⟩, rfl⟩) | ⟨l, ⟨d, ⟨hd, hb⟩, rfl⟩, hx⟩)
    · exact Or.inl h
    · exact Or.inr (Or.inl ⟨r, hr, hb, rfl⟩)
    · exact Or.inr (Or.inr ⟨d, hd, hb, hx⟩)
  · rintro (h | ⟨r, hr, hb, rfl⟩ | ⟨d, hd, hb, hx⟩)
    · exact Or.inl (Or.inl h)
    · exact Or.inl (Or.inr ⟨r, ⟨hr, hb⟩, rfl⟩)
    · exact Or.inr ⟨d.concl, ⟨d, ⟨hd, hb⟩, rfl⟩, hx⟩

theorem subset_step (T : Theory) (ds : List Dflt) (S : List Int) : ∀ x ∈ S, x ∈ step T ds S :=
  fun x hx => (step_mem T ds S x).2 (Or.inl hx)

theorem step_mono (T : Theory) (ds : List Dflt) (S S' : List Int) (h : ∀ x ∈ S, x ∈ S') :
    ∀ x ∈ step T ds S, x ∈ step T ds S' := by
  intro x hx
  rw [step_mem] at hx ⊢
  rcases hx with hx | ⟨r, hr, hb, e⟩ | ⟨d, hd, hb, hx⟩
  · exact Or.inl (h x hx)
  · exact Or.inr (Or.inl ⟨r, hr, fun y hy => h y (hb y hy), e⟩)
  · exact Or.inr (Or.inr ⟨d, hd, fun y hy => h y (hb y hy), hx⟩)

theorem iter_mem_W (T : Theory) (ds : List Dflt) (n : Nat) :
    ∀ x ∈ T.W, x ∈ iter T ds n T.W := by
  induction n with
  | zero => intro x hx; simpa [iter] using hx
  | succ n ih =>
    intro x hx
    rw [iter_succ]
    exact subset_step _ _ _ x (ih x hx)

theorem iter_mono_succ (T : Theory) (ds : List Dflt) (n : Nat) :
    ∀ x ∈ iter T ds n T.W, x ∈ iter T ds (n+1) T.W := by
  intro x hx
  rw [iter_succ]
  exact subset_step _ _ _ x hx

/-- 最小性の核 -/
theorem iter_least (T : Theory) (ds : List Dflt) (S : List Int) (hS : Closed T ds S) (n : Nat) :
    ∀ x ∈ iter T ds n T.W, x ∈ S := by
  induction n with
  | zero => intro x hx; exact hS.1 x (by simpa [iter] using hx)
  | succ n ih =>
    intro x hx
    rw [iter_succ, step_mem] at hx
    rcases hx with hx | ⟨r, hr, hb, e⟩ | ⟨d, hd, hb, hx⟩
    · exact ih x hx
    · exact e ▸ hS.2.1 r hr (fun y hy => ih y (hb y hy))
    · exact hS.2.2 d hd (fun y hy => ih y (hb y hy)) x hx

/-! ### 発火数 -/

def cnt (T : Theory) (ds : List Dflt) (S : List Int) : Nat :=
  (T.rules.filter (fun r => subsetL r.1 S)).length +
  (ds.filter (fun d => subsetL d.pre S)).length

theorem filter_len_mono {α : Type} (p q : α → Bool) (l : List α)
    (h : ∀ a ∈ l, p a = true → q a = true) :
    (l.filter p).length ≤ (l.filter q).length := by
  induction l with
  | nil => simp
  | cons a l ih =>
    have ih' := ih (fun b hb => h b (List.mem_cons_of_mem _ hb))
    have ha := h a (List.mem_cons_self)
    simp only [List.filter_cons]
    cases hp : p a <;> cases hq : q a <;> simp_all <;> omega

theorem filter_len_eq {α : Type} (p q : α → Bool) (l : List α)
    (h : ∀ a ∈ l, p a = true → q a = true)
    (hl : (l.filter q).length ≤ (l.filter p).length) :
    ∀ a ∈ l, q a = true → p a = true := by
  induction l with
  | nil => simp
  | cons a l ih =>
    have h' : ∀ b ∈ l, p b = true → q b = true := fun b hb => h b (List.mem_cons_of_mem _ hb)
    have ih' := ih h'
    have mono := filter_len_mono p q l h'
    have ha := h a (List.mem_cons_self)
    intro b hb hqb
    rcases List.mem_cons.1 hb with rfl | hb
    · cases hpb' : p b
      · simp only [List.filter_cons, hpb', hqb] at hl
        simp at hl
        omega
      · rfl
    · apply ih' _ b hb hqb
      simp only [List.filter_cons] at hl
      cases hp : p a <;> cases hq : q a <;> simp_all <;> omega

theorem subsetL_mono (a S S' : List Int) (h : ∀ x ∈ S, x ∈ S') :
    subsetL a S = true → subsetL a S' = true := by
  simp only [subsetL_iff]
  exact fun hb y hy => h y (hb y hy)

theorem cnt_mono (T : Theory) (ds : List Dflt) (S S' : List Int) (h : ∀ x ∈ S, x ∈ S') :
    cnt T ds S ≤ cnt T ds S' := by
  unfold cnt
  have h1 := filter_len_mono (fun r : List Int × Int => subsetL r.1 S)
    (fun r => subsetL r.1 S') T.rules (fun r _ => subsetL_mono _ _ _ h)
  have h2 := filter_len_mono (fun d : Dflt => subsetL d.pre S)
    (fun d => subsetL d.pre S') ds (fun d _ => subsetL_mono _ _ _ h)
  omega

theorem cnt_le (T : Theory) (E : List Int) (S : List Int) :
    cnt T (okDefaults T E) S ≤ T.rules.length + T.defaults.length := by
  unfold cnt okDefaults
  have h1 := List.length_filter_le (fun r : List Int × Int => subsetL r.1 S) T.rules
  have h2 := List.length_filter_le (fun d : Dflt => subsetL d.pre S)
    (T.defaults.filter (fun d => d.just.all (fun j => !E.contains (-j))))
  have h3 := List.length_filter_le (fun d : Dflt => d.just.all (fun j => !E.contains (-j)))
    T.defaults
  omega

/-- 不動点 -/
def Fixed (T : Theory) (ds : List Dflt) (S : List Int) : Prop :=
  ∀ x ∈ step T ds S, x ∈ S

theorem fixed_next (T : Theory) (ds : List Dflt) (S : List Int) (h : Fixed T ds S) :
    Fixed T ds (step T ds S) := by
  intro x hx
  exact step_mono T ds (step T ds S) S h x hx

theorem fixed_of_cnt (T : Theory) (ds : List Dflt) (S : List Int)
    (h : cnt T ds (step T ds S) ≤ cnt T ds S) : Fixed T ds (step T ds S) := by
  intro x hx
  have sub := subset_step T ds S
  unfold cnt at h
  have m1 := filter_len_mono (fun r : List Int × Int => subsetL r.1 S)
    (fun r => subsetL r.1 (step T ds S)) T.rules (fun r _ => subsetL_mono _ _ _ sub)
  have m2 := filter_len_mono (fun d : Dflt => subsetL d.pre S)
    (fun d => subsetL d.pre (step T ds S)) ds (fun d _ => subsetL_mono _ _ _ sub)
  rw [step_mem] at hx
  rcases hx with hx | ⟨r, hr, hb, e⟩ | ⟨d, hd, hb, hx⟩
  · exact hx
  · have e1 := filter_len_eq (fun r : List Int × Int => subsetL r.1 S)
      (fun r => subsetL r.1 (step T ds S)) T.rules (fun r _ => subsetL_mono _ _ _ sub)
      (by omega) r hr (by simpa [subsetL_iff] using hb)
    exact (step_mem T ds S x).2 (Or.inr (Or.inl ⟨r, hr, by simpa [subsetL_iff] using e1, e⟩))
  · have e1 := filter_len_eq (fun d : Dflt => subsetL d.pre S)
      (fun d => subsetL d.pre (step T ds S)) ds (fun d _ => subsetL_mono _ _ _ sub)
      (by omega) d hd (by simpa [subsetL_iff] using hb)
    exact (step_mem T ds S x).2 (Or.inr (Or.inr ⟨d, hd, by simpa [subsetL_iff] using e1, hx⟩))

theorem fixed_or_cnt (T : Theory) (E : List Int) (k : Nat) :
    Fixed T (okDefaults T E) (iter T (okDefaults T E) k T.W) ∨
      k ≤ cnt T (okDefaults T E) (iter T (okDefaults T E) k T.W) := by
  induction k with
  | zero => exact Or.inr (Nat.zero_le _)
  | succ k ih =>
    have e := iter_succ T (okDefaults T E) k T.W
    rw [e]
    rcases ih with h | h
    · exact Or.inl (fixed_next _ _ _ h)
    · by_cases hc : cnt T (okDefaults T E) (step T (okDefaults T E) (iter T (okDefaults T E) k T.W))
          ≤ cnt T (okDefaults T E) (iter T (okDefaults T E) k T.W)
      · exact Or.inl (fixed_of_cnt _ _ _ hc)
      · exact Or.inr (by omega)

theorem gamma_fixed (T : Theory) (E : List Int) :
    Fixed T (okDefaults T E) (gamma T E) := by
  unfold gamma
  rcases fixed_or_cnt T E (T.rules.length + T.defaults.length + 1) with h | h
  · exact h
  · have := cnt_le T E (iter T (okDefaults T E) (T.rules.length + T.defaults.length + 1) T.W)
    omega

/-! ## 定理 -/

theorem gamma_closed (T : Theory) (E : List Int) : Closed T (okDefaults T E) (gamma T E) := by
  have hf := gamma_fixed T E
  refine ⟨iter_mem_W _ _ _, ?_, ?_⟩
  · intro r hr hb
    exact hf _ ((step_mem _ _ _ _).2 (Or.inr (Or.inl ⟨r, hr, hb, rfl⟩)))
  · intro d hd hb c hc
    exact hf _ ((step_mem _ _ _ _).2 (Or.inr (Or.inr ⟨d, hd, hb, hc⟩)))

/-- Γ(E) は、閉じた集合のうち最小である -/
theorem gamma_least (T : Theory) (E : List Int) :
    ∀ S, Closed T (okDefaults T E) S → ∀ x ∈ gamma T E, x ∈ S :=
  fun S hS => iter_least T _ S hS _

/-- 健全性: Bool の判定 isExtension T E = true から、Reiter の Extension であることが従う -/
theorem isExtension_sound (T : Theory) (E : List Int) (h : isExtension T E = true) :
    ReiterExtension T E := by
  simp only [isExtension, Bool.and_eq_true, sameSet, subsetL_iff] at h
  obtain ⟨hc, hg, hg'⟩ := h
  have hcons : ∀ x ∈ E, -x ∉ E := by
    intro x hx hx'
    have := (List.all_eq_true.1 hc) x hx
    simp [hx'] at this
  refine ⟨hcons, ?_, ?_⟩
  · obtain ⟨a, b, c⟩ := gamma_closed T E
    exact ⟨fun x hx => hg x (a x hx),
      fun r hr hb => hg _ (b r hr (fun y hy => hg' y (hb y hy))),
      fun d hd hb c' hc' => hg _ (c d hd (fun y hy => hg' y (hb y hy)) c' hc')⟩
  · intro S hS x hx
    exact gamma_least T E S hS x (hg' x hx)


/-! ## 証明書による検査（0.6.0 以降の既定）

  Γ(E) を Lean の中で反復して計算し直す代わりに、mext が E の導出の列（証明書）を渡し、
  Lean はそれを確かめるだけにする。確かめるのは次の三つである。
  - 無矛盾: E は無矛盾（consistentL）。
  - 閉包: E は W を含み、すべての規則と、正当化が E と無矛盾なデフォルトについて閉じている（closedB）。
    これで Γ(E) ⊆ E になる（Γ(E) はこの性質をもつ最小の集合なので）。
  - 導出: W から始めて、証明書の各段（規則 i か、正当化が E と無矛盾なデフォルト i）を、前提が
    それまでに得られた集合に含まれる場合にだけ使い、最後に得られた集合が E を含む（runCert）。
    これで E ⊆ Γ(E) になる。
  反復の回数の上限を示す必要がなく、検査は証明書の長さと規則・デフォルトの数に比例する。
-/

/-- 証明書の一段: 規則 i か、デフォルト i を使う（i は T.rules / T.defaults の中の位置） -/
inductive Step where
  | rule (i : Nat)
  | dflt (i : Nat)
deriving Repr

/-- 一段を集合 S で使えるなら、加わるリテラルを返す -/
def stepConcl (T : Theory) (E : List Int) (S : List Int) : Step → Option (List Int)
  | .rule i =>
    match T.rules[i]? with
    | some r => if subsetL r.1 S then some [r.2] else none
    | none => none
  | .dflt i =>
    match T.defaults[i]? with
    | some d => if subsetL d.pre S && d.just.all (fun j => !E.contains (-j)) then some d.concl else none
    | none => none

/-- 証明書の各段を順に使い、最後に得られた集合を返す（使えない段があれば none） -/
def runCert (T : Theory) (E : List Int) : List Step → List Int → Option (List Int)
  | [], S => some S
  | s :: ss, S =>
    match stepConcl T E S s with
    | some c => runCert T E ss (S ++ c)
    | none => none

/-- E が W を含み、規則と、正当化が E と無矛盾なデフォルトについて閉じている -/
def closedB (T : Theory) (E : List Int) : Bool :=
  subsetL T.W E &&
  T.rules.all (fun r => !subsetL r.1 E || E.contains r.2) &&
  (okDefaults T E).all (fun d => !subsetL d.pre E || subsetL d.concl E)

/-- 証明書による Extension の検査 -/
def checkCert (T : Theory) (E : List Int) (cert : List Step) : Bool :=
  consistentL E && closedB T E &&
  match runCert T E cert T.W with
  | some S => subsetL E S
  | none => false

theorem runCert_min (T : Theory) (E : List Int) (S' : List Int)
    (hc : Closed T (okDefaults T E) S') :
    ∀ (cert : List Step) (S0 S : List Int), runCert T E cert S0 = some S →
      (∀ x ∈ S0, x ∈ S') → ∀ x ∈ S, x ∈ S' := by
  intro cert
  induction cert with
  | nil =>
    intro S0 S h h0
    simp only [runCert, Option.some.injEq] at h
    subst h; exact h0
  | cons s ss ih =>
    intro S0 S h h0
    simp only [runCert] at h
    cases hs : stepConcl T E S0 s with
    | none => rw [hs] at h; simp at h
    | some c =>
      rw [hs] at h
      simp only at h
      refine ih _ _ h ?_
      intro x hx
      rcases List.mem_append.1 hx with hx | hx
      · exact h0 x hx
      · cases s with
        | rule i =>
          simp only [stepConcl] at hs
          cases hr : T.rules[i]? with
          | none => rw [hr] at hs; simp at hs
          | some r =>
            rw [hr] at hs
            simp only at hs
            split at hs
            · rename_i hb
              simp only [Option.some.injEq] at hs
              subst hs
              have hmem : r ∈ T.rules := List.mem_of_getElem? hr
              have := hc.2.1 r hmem (fun y hy => h0 y ((subsetL_iff _ _).1 hb y hy))
              simp only [List.mem_singleton] at hx
              rw [hx]; exact this
            · simp at hs
        | dflt i =>
          simp only [stepConcl] at hs
          cases hd : T.defaults[i]? with
          | none => rw [hd] at hs; simp at hs
          | some d =>
            rw [hd] at hs
            simp only at hs
            split at hs
            · rename_i hb
              simp only [Option.some.injEq] at hs
              subst hs
              rw [Bool.and_eq_true] at hb
              have hmem : d ∈ T.defaults := List.mem_of_getElem? hd
              have hok : d ∈ okDefaults T E := by
                unfold okDefaults
                exact List.mem_filter.2 ⟨hmem, hb.2⟩
              exact hc.2.2 d hok (fun y hy => h0 y ((subsetL_iff _ _).1 hb.1 y hy)) x hx
            · simp at hs

/-- 健全性: 証明書の検査が通れば、Reiter の Extension である -/
theorem checkCert_sound (T : Theory) (E : List Int) (cert : List Step)
    (h : checkCert T E cert = true) : ReiterExtension T E := by
  unfold checkCert at h
  cases hr : runCert T E cert T.W with
  | none => rw [hr] at h; simp at h
  | some S =>
    rw [hr] at h
    simp only [Bool.and_eq_true] at h
    obtain ⟨⟨h1, h2⟩, h3⟩ := h
    unfold consistentL at h1
    unfold closedB at h2
    simp only [Bool.and_eq_true, List.all_eq_true, subsetL_iff, Bool.or_eq_true,
      Bool.not_eq_true', List.contains_iff_mem] at h1 h2
    obtain ⟨⟨hW, hR⟩, hD⟩ := h2
    have hS3 := (subsetL_iff _ _).1 h3
    have hclosed : Closed T (okDefaults T E) E := by
      refine ⟨hW, ?_, ?_⟩
      · intro r hr hb
        rcases hR r hr with h | h
        · have := (subsetL_iff _ _).2 hb
          rw [this] at h; exact absurd h (by simp)
        · exact h
      · intro d hd hb
        rcases hD d hd with h | h
        · have := (subsetL_iff _ _).2 hb
          rw [this] at h; exact absurd h (by simp)
        · exact h
    refine ⟨?_, hclosed, ?_⟩
    · intro x hx hx'
      have := h1 x hx
      have h' : E.contains (-x) = true := List.contains_iff_mem.2 hx'
      rw [h'] at this; exact absurd this (by simp)
    · intro S' hS' x hx
      exact runCert_min T E S' hS' cert T.W S hr hS'.1 x (hS3 x hx)


/-! ## preferred の検査（0.6.1 以降）

  preferred Extension の定義（docs/mext.md「優先順位を尊重する生成」）:
  E の生成デフォルト（前提が E に含まれ、正当化が E と無矛盾なもの）を一つずつ適用していく列 g1, g2, … があって、
  各 gi を適用する時点の集合 S（W と g1…g(i−1) の結論から規則で導けるもの）で、
  (i) gi の前提が S に含まれ、
  (ii) gi より優先される（優先順位の推移的な閉包で）デフォルト d が E の生成デフォルトでなく、しかも
       d の前提が E に含まれるなら、d の正当化のどれかの否定が S に含まれる（d はすでに打ち負かされている）。
  デフォルトは T.defaults の中の位置で指す。prio は (優先される側, される側) の組の並び。
-/

/-- 優先順位の推移的な閉包: a は b より優先される -/
inductive Higher (prio : List (Nat × Nat)) : Nat → Nat → Prop
  | base {a b : Nat} : (a, b) ∈ prio → Higher prio a b
  | trans {a b c : Nat} : Higher prio a b → Higher prio b c → Higher prio a c

/-- x は A から規則で導ける（A を含み規則で閉じた、どの集合にも入る） -/
def RuleDerivable (T : Theory) (A : List Int) (x : Int) : Prop :=
  ∀ P : Int → Prop, (∀ y ∈ A, P y) → (∀ r ∈ T.rules, (∀ y ∈ r.1, P y) → P r.2) → P x

/-- E の生成デフォルト: 前提が E に含まれ、正当化が E と無矛盾 -/
def Generating (E : List Int) (d : Dflt) : Prop :=
  (∀ x ∈ d.pre, x ∈ E) ∧ ∀ j ∈ d.just, -j ∉ E

/-- 対立するデフォルト: 前提は E に含まれるが、生成デフォルトではない -/
def Rival (E : List Int) (d : Dflt) : Prop :=
  (∀ x ∈ d.pre, x ∈ E) ∧ ¬ ∀ j ∈ d.just, -j ∉ E

/-- 位置の並び gs のデフォルトの結論を並べたもの -/
def conclOf (T : Theory) (gs : List Nat) : List Int :=
  ((gs.filterMap (fun i => T.defaults[i]?)).map (fun d => d.concl)).flatten

/-- E は優先順位 prio を尊重して生成される（preferred Extension の条件） -/
def PreferredGen (T : Theory) (prio : List (Nat × Nat)) (E : List Int) : Prop :=
  ∃ gs : List Nat,
    (∀ i d, T.defaults[i]? = some d → Generating E d → i ∈ gs) ∧
    (∀ i ∈ gs, ∃ d, T.defaults[i]? = some d ∧ Generating E d) ∧
    ∀ k (hk : k < gs.length), ∃ d, T.defaults[gs[k]]? = some d ∧
      (∀ x ∈ d.pre, RuleDerivable T (T.W ++ conclOf T (gs.take k)) x) ∧
      ∀ a da, Higher prio a gs[k] → T.defaults[a]? = some da → Rival E da →
        ∃ j ∈ da.just, RuleDerivable T (T.W ++ conclOf T (gs.take k)) (-j)

/-- Bool の判定: 生成デフォルトか -/
def genB (E : List Int) (d : Dflt) : Bool :=
  subsetL d.pre E && d.just.all (fun j => !E.contains (-j))

/-- Bool の判定: 対立するデフォルトか -/
def rivalB (E : List Int) (d : Dflt) : Bool :=
  subsetL d.pre E && !(d.just.all (fun j => !E.contains (-j)))

/-- デフォルト i を集合 S で適用するとき、i より優先される対立デフォルトがすべて打ち負かされているか（hi は閉包） -/
def blockedB (T : Theory) (E : List Int) (hi : List (Nat × Nat)) (S : List Int) (i : Nat) : Bool :=
  hi.all (fun p => p.2 != i ||
    match T.defaults[p.1]? with
    | some da => !rivalB E da || da.just.any (fun j => S.contains (-j))
    | none => true)

/-- 証明書を順に使い、デフォルトの各段で優先の条件を確かめる -/
def runPref (T : Theory) (E : List Int) (hi : List (Nat × Nat)) : List Step → List Int → Bool
  | [], _ => true
  | s :: ss, S =>
    match stepConcl T E S s with
    | some c =>
      (match s with
       | .dflt i => blockedB T E hi S i
       | .rule _ => true) && runPref T E hi ss (S ++ c)
    | none => false

/-- 証明書の中のデフォルトの位置 -/
def dfltIdx : List Step → List Nat
  | [] => []
  | .rule _ :: ss => dfltIdx ss
  | .dflt i :: ss => i :: dfltIdx ss

/-- hi は推移的に閉じている -/
def transClosedB (hi : List (Nat × Nat)) : Bool :=
  hi.all (fun p => hi.all (fun q => p.2 != q.1 || hi.contains (p.1, q.2)))

/-- preferred Extension の検査: Extension であること（checkCert）、hi が prio を含み推移的に閉じていること、
    すべての生成デフォルトが証明書に現れること、各デフォルトの段で優先の条件が成り立つこと -/
def checkPref (T : Theory) (E : List Int) (prio hi : List (Nat × Nat)) (cert : List Step) : Bool :=
  checkCert T E cert && prio.all (fun p => hi.contains p) && transClosedB hi &&
  (List.range T.defaults.length).all (fun i =>
    match T.defaults[i]? with
    | some d => !genB E d || (dfltIdx cert).contains i
    | none => true) &&
  runPref T E hi cert T.W

theorem ruleDerivable_mono (T : Theory) (A B : List Int) (x : Int) (h : RuleDerivable T A x)
    (hAB : ∀ y ∈ A, y ∈ B) : RuleDerivable T B x :=
  fun P hB hr => h P (fun y hy => hB y (hAB y hy)) hr

theorem higher_mem (prio hi : List (Nat × Nat)) (hprio : ∀ p ∈ prio, p ∈ hi)
    (htr : transClosedB hi = true) {a b : Nat} (h : Higher prio a b) : (a, b) ∈ hi := by
  induction h with
  | base hab => exact hprio _ hab
  | trans _ _ ih1 ih2 =>
    rename_i a b c
    unfold transClosedB at htr
    simp only [List.all_eq_true, Bool.or_eq_true, bne_iff_ne, ne_eq, List.contains_iff_mem,
      decide_eq_true_eq] at htr
    have := htr _ ih1 _ ih2
    rcases this with h | h
    · exact absurd rfl h
    · exact h

theorem rivalB_of_rival (E : List Int) (d : Dflt) (h : Rival E d) : rivalB E d = true := by
  obtain ⟨h1, h2⟩ := h
  unfold rivalB
  rw [Bool.and_eq_true]
  refine ⟨(subsetL_iff _ _).2 h1, ?_⟩
  cases ha : d.just.all (fun j => !E.contains (-j)) with
  | true =>
    exfalso; apply h2
    intro j hj hj'
    have := List.all_eq_true.1 ha j hj
    simp only [Bool.not_eq_true', List.contains_eq_mem, decide_eq_false_iff_not] at this
    exact this hj'
  | false => rfl

theorem conclOf_snoc (T : Theory) (pre : List Nat) (i : Nat) (d : Dflt)
    (hd : T.defaults[i]? = some d) : conclOf T (pre ++ [i]) = conclOf T pre ++ d.concl := by
  simp [conclOf, List.filterMap_append, hd]

theorem stepConcl_rule (T : Theory) (E S : List Int) (i : Nat) (c : List Int)
    (h : stepConcl T E S (.rule i) = some c) :
    ∃ r, T.rules[i]? = some r ∧ (∀ y ∈ r.1, y ∈ S) ∧ c = [r.2] := by
  simp only [stepConcl] at h
  cases hr : T.rules[i]? with
  | none => rw [hr] at h; simp at h
  | some r =>
    rw [hr] at h
    simp only at h
    split at h
    · rename_i hb
      simp only [Option.some.injEq] at h
      exact ⟨r, rfl, (subsetL_iff _ _).1 hb, h.symm⟩
    · simp at h

theorem stepConcl_dflt (T : Theory) (E S : List Int) (i : Nat) (c : List Int)
    (h : stepConcl T E S (.dflt i) = some c) :
    ∃ d, T.defaults[i]? = some d ∧ (∀ y ∈ d.pre, y ∈ S) ∧ (∀ j ∈ d.just, -j ∉ E) ∧ c = d.concl := by
  simp only [stepConcl] at h
  cases hr : T.defaults[i]? with
  | none => rw [hr] at h; simp at h
  | some d =>
    rw [hr] at h
    simp only at h
    split at h
    · rename_i hb
      simp only [Option.some.injEq, Bool.and_eq_true] at h hb
      refine ⟨d, rfl, (subsetL_iff _ _).1 hb.1, ?_, h.symm⟩
      intro j hj hj'
      have := List.all_eq_true.1 hb.2 j hj
      simp only [Bool.not_eq_true', List.contains_eq_mem, decide_eq_false_iff_not] at this
      exact this hj'
    · simp at h

theorem runPref_cons (T : Theory) (E : List Int) (hi : List (Nat × Nat)) (s : Step) (ss : List Step)
    (S : List Int) (h : runPref T E hi (s :: ss) S = true) :
    ∃ c, stepConcl T E S s = some c ∧ runPref T E hi ss (S ++ c) = true ∧
      ∀ i, s = .dflt i → blockedB T E hi S i = true := by
  simp only [runPref] at h
  cases hs : stepConcl T E S s with
  | none => rw [hs] at h; simp at h
  | some c =>
    rw [hs] at h
    simp only [Bool.and_eq_true] at h
    refine ⟨c, rfl, h.2, ?_⟩
    intro i hi'
    subst hi'
    exact h.1

theorem stepConcl_sub (T : Theory) (E : List Int) (hc : Closed T (okDefaults T E) E)
    (S : List Int) (hS : ∀ x ∈ S, x ∈ E) (s : Step) (c : List Int)
    (h : stepConcl T E S s = some c) : ∀ x ∈ c, x ∈ E := by
  cases s with
  | rule i =>
    obtain ⟨r, hr, hsub, rfl⟩ := stepConcl_rule _ _ _ _ _ h
    intro x hx
    simp only [List.mem_singleton] at hx
    rw [hx]
    exact hc.2.1 r (List.mem_of_getElem? hr) (fun y hy => hS y (hsub y hy))
  | dflt i =>
    obtain ⟨d, hd, hpre, hjust, rfl⟩ := stepConcl_dflt _ _ _ _ _ h
    intro x hx
    have hok : d ∈ okDefaults T E := by
      unfold okDefaults
      refine List.mem_filter.2 ⟨List.mem_of_getElem? hd, ?_⟩
      rw [List.all_eq_true]
      intro j hj
      simp only [Bool.not_eq_true', List.contains_eq_mem, decide_eq_false_iff_not]
      exact hjust j hj
    exact hc.2.2 d hok (fun y hy => hS y (hpre y hy)) x hx

theorem runPref_gen (T : Theory) (E : List Int) (hc : Closed T (okDefaults T E) E)
    (hi : List (Nat × Nat)) :
    ∀ (cert : List Step) (S : List Int), runPref T E hi cert S = true → (∀ x ∈ S, x ∈ E) →
      ∀ i ∈ dfltIdx cert, ∃ d, T.defaults[i]? = some d ∧ Generating E d := by
  intro cert
  induction cert with
  | nil => intro S _ _ i hi'; simp [dfltIdx] at hi'
  | cons s ss ih =>
    intro S h hE i hi'
    obtain ⟨c, hs, hrest, _⟩ := runPref_cons _ _ _ _ _ _ h
    have hE' : ∀ x ∈ S ++ c, x ∈ E := by
      intro x hx
      rcases List.mem_append.1 hx with hx | hx
      · exact hE x hx
      · exact stepConcl_sub T E hc S hE s c hs x hx
    cases s with
    | rule j => exact ih _ hrest hE' i hi'
    | dflt j =>
      simp only [dfltIdx, List.mem_cons] at hi'
      rcases hi' with rfl | hi'
      · obtain ⟨d, hd, hpre, hjust, rfl⟩ := stepConcl_dflt _ _ _ _ _ hs
        exact ⟨d, hd, fun x hx => hE x (hpre x hx), hjust⟩
      · exact ih _ hrest hE' i hi'

theorem runPref_main (T : Theory) (E : List Int) (hc : Closed T (okDefaults T E) E)
    (prio hi : List (Nat × Nat)) (hprio : ∀ p ∈ prio, p ∈ hi) (htr : transClosedB hi = true) :
    ∀ (cert : List Step) (pre : List Nat) (S : List Int), runPref T E hi cert S = true →
      (∀ x ∈ S, x ∈ E) → (∀ x ∈ S, RuleDerivable T (T.W ++ conclOf T pre) x) →
      ∀ k (hk : k < (dfltIdx cert).length), ∃ d, T.defaults[(dfltIdx cert)[k]]? = some d ∧
        (∀ x ∈ d.pre, RuleDerivable T (T.W ++ conclOf T (pre ++ (dfltIdx cert).take k)) x) ∧
        ∀ a da, Higher prio a (dfltIdx cert)[k] → T.defaults[a]? = some da → Rival E da →
          ∃ j ∈ da.just, RuleDerivable T (T.W ++ conclOf T (pre ++ (dfltIdx cert).take k)) (-j) := by
  intro cert
  induction cert with
  | nil => intro pre S _ _ _ k hk; simp [dfltIdx] at hk
  | cons s ss ih =>
    intro pre S h hE hR k hk
    obtain ⟨c, hs, hrest, hb⟩ := runPref_cons _ _ _ _ _ _ h
    have hE' : ∀ x ∈ S ++ c, x ∈ E := by
      intro x hx
      rcases List.mem_append.1 hx with hx | hx
      · exact hE x hx
      · exact stepConcl_sub T E hc S hE s c hs x hx
    cases s with
    | rule i =>
      obtain ⟨r, hr, hsub, rfl⟩ := stepConcl_rule _ _ _ _ _ hs
      refine ih pre (S ++ [r.2]) hrest hE' ?_ k hk
      intro x hx
      rcases List.mem_append.1 hx with hx | hx
      · exact hR x hx
      · simp only [List.mem_singleton] at hx
        rw [hx]
        intro P hA hr'
        exact hr' r (List.mem_of_getElem? hr) (fun y hy => hR y (hsub y hy) P hA hr')
    | dflt i =>
      obtain ⟨d, hd, hpre, hjust, rfl⟩ := stepConcl_dflt _ _ _ _ _ hs
      have hb' := hb i rfl
      cases k with
      | zero =>
        refine ⟨d, ?_, ?_, ?_⟩
        · simpa [dfltIdx] using hd
        · intro x hx
          simpa [dfltIdx] using hR x (hpre x hx)
        · intro a da hh hda hrv
          have hh' : Higher prio a i := by simpa [dfltIdx] using hh
          have hmem := higher_mem prio hi hprio htr hh'
          unfold blockedB at hb'
          have := List.all_eq_true.1 hb' _ hmem
          simp only [hda, rivalB_of_rival E da hrv, Bool.or_eq_true, bne_iff_ne, ne_eq,
            not_true_eq_false, decide_false, Bool.false_or, Bool.not_true, List.any_eq_true,
            List.contains_iff_mem, decide_eq_true_eq, Bool.or_false] at this
          rcases this with h0 | ⟨j, hj, hj'⟩
          · exact absurd h0 id
          exact ⟨j, hj, by simpa [dfltIdx] using hR _ hj'⟩
      | succ k =>
        have hk' : k < (dfltIdx ss).length := by simp [dfltIdx] at hk; omega
        have hE'' := hE'
        have hR' : ∀ x ∈ S ++ d.concl, RuleDerivable T (T.W ++ conclOf T (pre ++ [i])) x := by
          intro x hx
          rw [conclOf_snoc T pre i d hd]
          rcases List.mem_append.1 hx with hx | hx
          · exact ruleDerivable_mono _ _ _ _ (hR x hx) (by
              intro y hy
              rcases List.mem_append.1 hy with hy | hy
              · exact List.mem_append_left _ hy
              · exact List.mem_append_right _ (List.mem_append_left _ hy))
          · intro P hA _
            exact hA x (List.mem_append_right _ (List.mem_append_right _ hx))
        have := ih (pre ++ [i]) (S ++ d.concl) hrest hE' hR' k hk'
        have e : pre ++ (dfltIdx (Step.dflt i :: ss)).take (k+1) = (pre ++ [i]) ++ (dfltIdx ss).take k := by
          simp [dfltIdx]
        rw [e]
        simpa [dfltIdx] using this

/-- 健全性: preferred の検査が通れば、E は Reiter の Extension で、優先順位を尊重して生成される -/
theorem checkPref_sound (T : Theory) (E : List Int) (prio hi : List (Nat × Nat)) (cert : List Step)
    (h : checkPref T E prio hi cert = true) : ReiterExtension T E ∧ PreferredGen T prio E := by
  have hce : ReiterExtension T E := by
    apply checkCert_sound T E cert
    unfold checkPref at h
    simp only [Bool.and_eq_true] at h
    exact h.1.1.1.1
  refine ⟨hce, dfltIdx cert, ?_, ?_, ?_⟩
  all_goals unfold checkPref at h
  all_goals simp only [Bool.and_eq_true] at h
  all_goals obtain ⟨⟨⟨⟨_, h2⟩, h3⟩, h4⟩, h5⟩ := h
  · intro i d hd hg
    have hlt : i < T.defaults.length := (List.getElem?_eq_some_iff.1 hd).1
    have := List.all_eq_true.1 h4 i (List.mem_range.2 hlt)
    rw [hd] at this
    have hgB : genB E d = true := by
      unfold genB
      rw [Bool.and_eq_true]
      refine ⟨(subsetL_iff _ _).2 hg.1, ?_⟩
      rw [List.all_eq_true]
      intro j hj
      simp only [Bool.not_eq_true', List.contains_eq_mem, decide_eq_false_iff_not]
      exact hg.2 j hj
    simp only [hgB, Bool.not_true, Bool.false_or, List.contains_iff_mem] at this
    exact this
  · exact runPref_gen T E hce.2.1 hi cert T.W h5 hce.2.1.1
  · have hprio : ∀ p ∈ prio, p ∈ hi := by
      intro p hp
      exact List.contains_iff_mem.1 (List.all_eq_true.1 h2 p hp)
    intro k hk
    have := runPref_main T E hce.2.1 prio hi hprio h3 cert [] T.W h5 hce.2.1.1
      (fun x hx P hA _ => hA x (by simp [conclOf, hx])) k hk
    simpa [conclOf] using this

end Mext

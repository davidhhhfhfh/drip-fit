import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Drip Fit - Elite Dashboard", layout="wide")

# تصميم واجهة المستخدم الاحترافية
st.markdown("""
    <div style="background-color:#0f172a; padding:25px; border-radius:15px; text-align:center; margin-bottom:30px; border: 1px solid #1e293b;">
        <h1 style="color:#f8fafc; margin:0; font-family: 'Cairo', sans-serif;">🚀 النظام الذكي الشامل لإدارة حسابات Drip Fit</h1>
        <p style="color:#38bdf8; margin:8px 0 0 0; font-size:16px; font-weight:bold;">فلترة ذكية، تحليلات مالية متقدمة، ونظام رصد نسب الإلغاء والمرتجعات</p>
    </div>
""", unsafe_allow_html=True)

# دالة ذكية لقراءة ودمج ملفات متعددة (سواء كانت Excel أو CSV)
def load_and_combine_files(uploaded_files):
    combined_df = pd.DataFrame()
    for file in uploaded_files:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        combined_df = pd.concat([combined_df, df], ignore_index=True)
    return combined_df

# تقسيم الشاشة لرفع الملفات (يدعم رفع أكثر من ملف في نفس الوقت)
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📁 شيتات الأوردرات الأصلية")
    store_files = st.file_uploader("يمكنك اختيار ملف واحد أو عدة ملفات معاً (DripFit Orders)", type=["csv", "xlsx"], accept_multiple_files=True)

with col2:
    st.markdown("### 🚚 شيتات المرتجعات والشحن")
    shipping_files = st.file_uploader("يمكنك اختيار ملف واحد أو عدة ملفات معاً (Returns/Shipping)", type=["csv", "xlsx"], accept_multiple_files=True)

# بدء المعالجة فور رفع الملفات
if store_files and shipping_files:
    try:
        # دمج وقراءة الملفات المرفوعة
        df_store = load_and_combine_files(store_files)
        df_shipping = load_and_combine_files(shipping_files)
        
        # تنظيف أسماء الأعمدة من المسافات الزائدة
        df_store.columns = df_store.columns.str.strip()
        df_shipping.columns = df_shipping.columns.str.strip()
        
        st.success(f"✅ تم دمج ومعالجة ({len(store_files)}) شيت أوردرات و ({len(shipping_files)}) شيت شحن بنجاح!")
        
        # دالة تنظيف الهواتف للمطابقة الاحتياطية القوية
        def clean_phone(val):
            if pd.isna(val): return ""
            s = str(val).split('.')[0].strip()
            if s.startswith('0'): s = s[1:]
            return s

        # --- 1. تصفية وفلترة المرتجعات ---
        # عزل المرتجعات فقط بناءً على الحالة الشهيرة في ملفاتك
        df_returns_only = df_shipping[df_shipping['حالة الشحنة'] == 'تم الارتجاع للراسل'].copy()
        
        returned_ids = df_returns_only['رقم الطلب'].astype(str).str.strip().dropna().unique()
        return_phones = set(df_returns_only['موبايل 1'].apply(clean_phone).tolist() + df_returns_only['موبايل 2'].apply(clean_phone).tolist()) - {"", "0"}
        
        # تنظيف شيت المتجر استعداداً للربط والحذف
        df_store['ID_str'] = df_store['ID'].astype(str).str.strip()
        df_store['phone1_clean'] = df_store['Tel1'].apply(clean_phone)
        df_store['phone2_clean'] = df_store['Tel2'].apply(clean_phone)
        
        # قاعدة الحذف الذكية (بالـ ID أو بالموبايل)
        is_returned = (
            df_store['ID_str'].isin(returned_ids) | 
            df_store['phone1_clean'].isin(return_phones) | 
            df_store['phone2_clean'].isin(return_phones)
        )
        
        # إنتاج الشيت الصافي (بدون مرتجعات)
        df_clean_orders = df_store[~is_returned].copy()
        
        # --- 2. الحسابات الذكية والمتقدمة داخل الشيت الصافي ---
        # أ) حساب عدد القطع في كل أوردر
        def count_items(item_str):
            if pd.isna(item_str): return 0
            return len(str(item_str).split('|'))
        df_clean_orders['إجمالي القطع في الأوردر'] = df_clean_orders['Item'].apply(count_items)
        
        # ب) جلب تكلفة الشحن الفعلية من شيت شركة الشحن، والافتراضي 70 ج.م
        shipping_cost_dict = pd.Series(df_shipping['تكلفة الشحن'].values, index=df_shipping['رقم الطلب'].astype(str).str.strip()).to_dict()
        df_clean_orders['تكلفة الشحن المتوقعة'] = df_clean_orders['ID_str'].map(shipping_cost_dict).fillna(70.0)
        
        # ج) حساب الإجمالي النهائي الشامل بالشحن لكل أوردر متبقي
        df_clean_orders['Price'] = pd.to_numeric(df_clean_orders['Price'], errors='coerce').fillna(0)
        df_clean_orders['الإجمالي بالشحن'] = df_clean_orders['Price'] + df_clean_orders['تكلفة الشحن المتوقعة']
        
        # تنظيف شيت الإخراج النهائي ليعود بنفس مظهره الأصلي الفخم
        df_export = df_clean_orders.drop(columns=['ID_str', 'phone1_clean', 'phone2_clean'], errors='ignore')
        
        # --- 3. عرض مؤشرات الأداء والماليات المتقدمة (KPIs) ---
        total_orders_uploaded = len(df_store)
        clean_orders_count = len(df_clean_orders)
        total_returns_deleted = total_orders_uploaded - clean_orders_count
        
        # حساب الحسابات المالية وقطع الملابس
        total_pieces_delivered = int(df_clean_orders['إجمالي القطع في الأوردر'].sum())
        total_net_revenue = df_clean_orders['Price'].sum()
        total_grand_amount = df_clean_orders['الإجمالي بالشحن'].sum()
        
        # حساب نسبة المرتجعات العامة ونسبة الإلغاء الفعلي
        return_rate = (total_returns_deleted / total_orders_uploaded * 100) if total_orders_uploaded > 0 else 0
        
        # حساب نسبة الإلغاء الدقيقة بناءً على أسباب فشل التسليم (العميل لغى الأوردر أو بكنسل)
        cancellation_reasons = ['العميل لغى الاوردر', 'العميل بيكنسل']
        if 'اسباب فشل التسليم' in df_returns_only.columns:
            total_canceled_orders = df_returns_only['اسباب فشل التسليم'].isin(cancellation_reasons).sum()
        else:
            total_canceled_orders = 0
        cancellation_rate = (total_canceled_orders / total_orders_uploaded * 100) if total_orders_uploaded > 0 else 0
        
        st.markdown("### 📊 الملخص المالي والتشغيلي المدمج")
        
        # عرض الصف الأول من المؤشرات الأساسية
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("📦 الأوردرات الصافية الناجحة", f"{clean_orders_count} أوردر", f"تم مسح {total_returns_deleted} مرتجع")
        kpi2.metric("👕 قطع الملابس المبيعة", f"{total_pieces_delivered} قطعة")
        kpi3.metric("💰 صافي قيمة المنتجات", f"{total_net_revenue:,.1f} ج.م")
        kpi4.metric("🧾 إجمالي التحصيل بالشحن", f"{total_grand_amount:,.1f} ج.م")
        
        # عرض الصف الثاني من نسب الأداء الحساسة (المرتجعات والإلغاء)
        st.write("")
        col_rates1, col_rates2 = st.columns(2)
        with col_rates1:
            st.metric("🔄 نسبة المرتجعات الإجمالية", f"{return_rate:.1f}%", help="إجمالي الشحنات التي عادت للراسل منسوبة لكل الأوردرات المرفوعة")
        with col_rates2:
            st.metric("🛑 نسبة الإلغاء الفعلي للعملاء", f"{cancellation_rate:.1f}%", delta=f"{total_canceled_orders} أوردر ملغي", delta_color="inverse", help="النسبة المئوية للأوردرات التي قام العميل بإلغائها بنفسه")
        
        st.markdown("---")
        
        # --- 4. الخريطة الذهنية الموزعة بالعرض (Horizontal Mind Map Layout) ---
        st.markdown("### 🧠 الخريطة الذهنية وتحليل أسباب الارتجاع (موزعة أفقياً)")
        st.write("تحليل جذور المشاكل مقسمة في كتل عريضة متوازية لتسهيل المقارنة واتخاذ القرار:")
        
        if 'اسباب فشل التسليم' in df_returns_only.columns:
            reason_counts = df_returns_only['اسباب فشل التسليم'].value_counts()
            
            if not reason_counts.empty:
                # إنشاء 3 أعمدة رئيسية لعرض الخريطة الذهنية بالعرض
                mind_col1, mind_col2, mind_col3 = st.columns(3)
                
                with mind_col1:
                    st.markdown(f"""
                    <div style="background-color:#1e293b; padding:15px; border-radius:10px; min-height:180px; border-top: 5px solid #ef4444;">
                        <h4 style="color:#f8fafc; margin:0 0 10px 0;">🛑 أسباب سلوك وقرار العميل</h4>
                        <ul style="color:#cbd5e1; padding-right:20px; font-size:14px; direction:rtl;">
                            <li><b>العميل لغى الأوردر أو كنسل:</b> {reason_counts.get('العميل لغى الاوردر', 0) + reason_counts.get('العميل بيكنسل', 0)} أوردر (نسبة إلغاء {cancellation_rate:.1f}%)</li>
                            <li><b>العميل لا يرد على الهاتف:</b> {reason_counts.get('العميل لا يرد', 0)} أوردر</li>
                            <li><b>رفض دفع مصاريف الشحن:</b> {reason_counts.get('العميل رفض دفع الشحن', 0)} أوردر</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with mind_col2:
                    st.markdown(f"""
                    <div style="background-color:#1e293b; padding:15px; border-radius:10px; min-height:180px; border-top: 5px solid #eab308;">
                        <h4 style="color:#f8fafc; margin:0 0 10px 0;">🏷️ أسباب السيستم والمنتج</h4>
                        <ul style="color:#cbd5e1; padding-right:20px; font-size:14px; direction:rtl;">
                            <li><b>شحنات مكررة بالخطأ:</b> {reason_counts.get('شحنة مكررة', 0)} أوردر</li>
                            <li><b>اختلاف سعر المنتج:</b> {reason_counts.get('اختلاف سعر المنتج', 0)} أوردر</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with mind_col3:
                    st.markdown(f"""
                    <div style="background-color:#1e293b; padding:15px; border-radius:10px; min-height:180px; border-top: 5px solid #3b82f6;">
                        <h4 style="color:#f8fafc; margin:0 0 10px 0;">📍 أسباب جغرافية ولوجستية</h4>
                        <ul style="color:#cbd5e1; padding-right:20px; font-size:14px; direction:rtl;">
                            <li><b>منطقة غير مخدومة/خارج النطاق:</b> {reason_counts.get('منطقة غير مخدومة', 0)} أوردر</li>
                            <li><b>تحويل الشحنة لمنطقة أخرى:</b> {reason_counts.get('تحويل لمنطقة اخري', 0)} أوردر</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.write("") # مسافة بصرية
                # عرض رسم بياني فخم مكمل للخريطة الذهنية
                st.bar_chart(reason_counts)
            else:
                st.info("لا توجد تفاصيل أسباب مسجلة داخل شيتات المرتجعات المرفوعة.")
        else:
            st.warning("عمود 'اسباب فشل التسليم' غير موجود في شيت الشحن لتوليد الخريطة الذهنية.")
            
        st.markdown("---")
        
        # --- 5. تحليل المنتجات والمحافظات الأكثر طلباً ---
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("### 🏆 المنتجات الأكثر مبيعاً (في الشيت الصافي)")
            all_items = []
            for items in df_clean_orders['Item'].dropna():
                all_items.extend([i.strip() for i in str(items).split('|')])
            if all_items:
                df_items_chart = pd.DataFrame(pd.Series(all_items).value_counts()).reset_index()
                df_items_chart.columns = ['المنتج والمقاس', 'القطع المطلوبة']
                st.dataframe(df_items_chart.head(8), use_container_width=True, hide_index=True)
                
        with col_right:
            st.markdown("### 📍 المناطق والمحافظات الأكثر تفاعلاً")
            if 'Area' in df_clean_orders.columns:
                area_counts = df_clean_orders['Area'].value_counts().head(8)
                st.bar_chart(area_counts)
            else:
                st.info("لم يتم العثور على عمود 'Area' لتحليل المناطق.")
                
        st.markdown("---")
        
        # --- 6. قسم تحميل الشيت الجديد الجاهز المطور ---
        st.markdown("### 📥 تحميل الشيت المدمج والمصفّى النهائي")
        st.info("💡 الشيت الجاهز للتحميل يدمج كافة الملفات التي رفعتها، ويحتوي على الأعمدة الحسابية الجديدة (إجمالي القطع، تكلفة الشحن المتوقعة، الإجمالي بالشحن).")
        
        # تصدير الملف بصيغة إكسيل احترافية في الذاكرة
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False, sheet_name='DripFit_Final_Clean')
            
        st.download_button(
            label="⚡ تحميل ملف Drip Fit النهائي المطور والجاهز فوراً (Excel)",
            data=buffer.getvalue(),
            file_name="Drip_Fit_Mega_Clean_Orders.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        st.error(f"حدث خطأ أثناء دمج وتحليل البيانات: {e}")

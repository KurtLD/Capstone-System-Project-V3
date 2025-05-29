from django.contrib import admin
from django.urls import include, path
from reco_app import views as reco_views
from scheduler_app import views as scheduler_views
from users.views import (
    signup_view, 
    login_view,
    logout_view,
    ForgotPasswordView,
    VerifyOTPView,
    ResetPasswordView,
    admin_dashboard,
    school_year_selection, 
    select_school_year,
    faculty_dashboard,
    # view_all_schedules, 
    account_settings,
    evaluate_capstone,
    audit_logs,
    faculty_logs,
    title_hearing_view,
    pre_oral_defense_view,
    mock_defense_view,
    final_defense_view,
    adviser_records_view,
    mock_adviser_records_view,
    final_adviser_records_view,
    pre_oral_class_record,
    pre_oral_individual_class_record,
    mock_class_record,
    mock_individual_class_record,
    final_class_record,
    final_individual_class_record,
    individual_combined_class_record,

    # the following view function is used for the PreOral
    add_section,
    edit_section,
    delete_section,
    get_section_details,

    add_criteria,
    edit_criteria,
    delete_criteria,
    # get_verdict_checkboxes,
    view_criteria,
    view_section,

    add_criteria_description,
    edit_criteria_description,
    delete_criteria_description,

    add_verdict,
    edit_verdict,
    delete_verdict,
    
    input_grade,
    evaluate_capstone,
    update_evaluate_capstone,
    adviser_record_detail,
    reco,

    # the following view functions are used for the mock defense
    mock_add_section,
    mock_edit_section,
    mock_delete_section,
    mock_get_section_details,

    mock_add_criteria,
    mock_edit_criteria,
    mock_delete_criteria,

    mock_add_criteria_description,
    mock_edit_criteria_description,
    mock_delete_criteria_description,
    
    mock_add_verdict,
    mock_edit_verdict,
    mock_delete_verdict,

    mock_view_criteria,
    mock_view_section,

    mock_input_grade,
    mock_evaluate_capstone,
    mock_update_evaluate_capstone,
    mock_adviser_record_detail,
    mock_reco,


    # the following view functions are used for the final defense
    final_add_section,
    final_edit_section,
    final_delete_section,
    final_get_section_details,

    final_add_criteria,
    final_edit_criteria,
    final_delete_criteria,

    final_add_criteria_description,
    final_edit_criteria_description,
    final_delete_criteria_description,
    
    final_add_verdict,
    final_edit_verdict,
    final_delete_verdict,

    final_view_section,

    final_input_grade,
    final_evaluate_capstone,
    final_update_evaluate_capstone,
    final_adviser_record_detail,
    final_reco,

    # the following view function is used to clone evalauation form
    pre_oral_clone_records,
    mock_clone_records,
    final_clone_records,

    # the following view functions are used to view the evaluation form
    view_input_grade,
    view_mock_input_grade,
    view_final_input_grade,

    #the following function is used for creating new/backup admin
    create_new_account,

    # the following funnctions are for the accepting and declining the advisee
    accept_adviser,
    decline_adviser,

    # the following functions are for the notifications
    notification_list,
    mark_notification_as_read,
    mark_all_notifications_as_read,

    accept_adviser_and_mark_read,
    decline_adviser_and_mark_read,
    developer_profile
)

urlpatterns = [
    # Users related URL patterns
    path('admin/', admin.site.urls),
    path('faqs/', include('A_FAQs.urls')),
    path('developer-profile/', developer_profile, name='developer_profile'),
    path('', login_view, name='login'),
    path('signup/', signup_view, name='signup'),  
    path('logout/', logout_view, name='logout'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    path('admin_dashboard/', admin_dashboard, name='admin_dashboard'),  
    path('faculty_dashboard/', faculty_dashboard, name='faculty_dashboard'),  
    path('account_settings/', account_settings, name='account_settings'),
    path('account_settings/', account_settings, name='faculty_account_settings'), 
    path('accounts/profile/', account_settings, name='profile'),  # Redirect profile to account_settings
    path('audit-logs/', audit_logs, name='audit_logs'),
    path('faculty-logs/', faculty_logs, name='faculty_logs'),
    path('title_hearing/', title_hearing_view, name='title_hearing'),
    path('pre_oral_defense/', pre_oral_defense_view, name='pre_oral_defense'),
    path('mock_defense/', mock_defense_view, name='mock_defense'),
    path('final_defense/', final_defense_view, name='final_defense'),
    path('adviser_records/', adviser_records_view, name='adviser_records'),
    path('mock-adviser_records/', mock_adviser_records_view, name='mock_adviser_records'),
    path('final-adviser_records/', final_adviser_records_view, name='final_adviser_records'),
    path('pre-oral-class-record/', pre_oral_class_record, name='class_record'),
    path('pre_oral_individual_class_record/', pre_oral_individual_class_record, name='pre_oral_individual_class_record'),
    path('mock_individual_class_record/', mock_individual_class_record, name='mock_individual_class_record'),
    path('mock-class-record/', mock_class_record, name='mock_class_record'),
    path('final_individual_class_record/', final_individual_class_record, name='final_individual_class_record'),
    path('final-class-record/', final_class_record, name='final_class_record'),
    path('school-year-selection/', school_year_selection, name='school_year_selection'),  
    path('select_school_year/', select_school_year, name='select_school_year'),

    path('records/combined/', individual_combined_class_record, name='combined_class_record'),


    # Recommend adviser URL pattern
    path('recommend_adviser/', reco_views.recommend_faculty, name='recommend_adviser'),
    path('recommend_faculty_again/<int:adviser_id>/', reco_views.recommend_faculty_again, name='recommend_faculty_again'),

    # Faculty related URL patterns
    path('add_faculty/', reco_views.add_faculty, name='add_faculty'),
    path('faculty_list/', reco_views.faculty_list, name='faculty_list'),
    path('disabled_faculty_list/', reco_views.disabled_faculty_list, name='disabled_faculty_list'),
    path('update_faculty/<int:pk>/', reco_views.update_faculty, name='update_faculty'),
    path('disable_faculty/<int:pk>/', reco_views.disable_faculty, name='disable_faculty'),
    path('enable_faculty/<int:pk>/', reco_views.enable_faculty, name='enable_faculty'),
    path('assign_capstone_teacher/<int:faculty_id>/', reco_views.assign_capstone_teacher, name='assign_capstone_teacher'),
    path('remove_capstone_teacher/<int:faculty_id>/', reco_views.remove_capstone_teacher, name='remove_capstone_teacher'),
    path('faculty/delete/<int:pk>/', reco_views.delete_faculty, name='delete_faculty'),
    
    # Adviser related URL patterns
    path('adviser_info/', reco_views.adviser_info, name='adviser_info'),
    path('adviser_info/<int:title_id>/', reco_views.adviser_info, name='adviser_info'),
    path('adviser_list/', reco_views.adviser_list, name='adviser_list'),
    path('save-adviser/', reco_views.save_adviser, name='save_adviser'),
    path('update_adviser/<int:title_id>/', reco_views.update_adviser, name='update_adviser'),
    path('update_adviser2/<int:title_id>/', reco_views.update_adviser2, name='update_adviser2'),
    path('delete_adviser/<int:adviser_id>/', reco_views.delete_adviser, name='delete_adviser'),

    # Room related urls
    path('rooms/', scheduler_views.room_list, name='room_list'),
    path('edit/<int:pk>/', scheduler_views.room_edit, name='room_edit'),
    path('delete/<int:pk>/', scheduler_views.room_delete, name='room_delete'),

    # Title hearing schedule related URL patterns
    path('faculty-availability/', scheduler_views.faculty_availability, name='faculty_availability'),
    path('save-faculty-specific-unavailability/', scheduler_views.save_faculty_specific_unavailability, name='save_specific'),
    path('get-faculty-specific-unavailability/', scheduler_views.get_faculty_specific_unavailability, name='get_specific'),
    path('save-faculty-unavailable-slots/', scheduler_views.save_faculty_unavailable_slots, name='save_slots'),
    path('get-faculty-unavailable-slots/', scheduler_views.get_faculty_unavailable_slots, name='get_slots'),
    # Optional: Keep these for backward compatibility
    path('save-faculty-unavailable-dates/', scheduler_views.save_faculty_unavailable_dates, name='save_dates'),
    path('get-faculty-unavailable-dates/', scheduler_views.get_faculty_unavailable_dates, name='get_dates'),


    path('checker1/', scheduler_views.checker1, name='checker1'),
    path('add_group/', scheduler_views.add_group, name='add_group'),
    path('groups/', scheduler_views.group_info_list, name='group_info_list'),
    path('group/<int:id>/update/', scheduler_views.update_group, name='update_group'),
    path('group/<int:group_id>/delete/', scheduler_views.delete_group, name='delete_group'),
    path('schedule_list/', scheduler_views.schedule_list, name='schedule_list'),
    path('reschedule/<int:schedule_id>/', scheduler_views.reschedule, name='reschedule'),
    path('reassign/<int:schedule_id>/', scheduler_views.reassign, name='reassign'),
    path('faculty-tally/', scheduler_views.faculty_tally_view, name='faculty_tally'),
    path('reset-schedule/', scheduler_views.reset_schedule, name='reset_schedule'),
    # for exporting
    path('export/excel/', scheduler_views.export_schedules_excel, name='export_schedules_excel'),
    path('export/pdf/', scheduler_views.export_schedules_pdf, name='export_schedules_pdf'),
    
    # Pre-oral defense schedule related URL patterns
    path('checker2/', scheduler_views.checker2, name='checker2'),
    path('add_groupPOD/', scheduler_views.add_groupPOD, name='add_groupPOD'),
    path('groupsPOD/', scheduler_views.group_infoPOD, name='group_infoPOD'),
    path('schedule_listPOD/', scheduler_views.schedule_listPOD, name='schedule_listPOD'),
    path('reschedulePOD/<int:schedulePOD_id>/', scheduler_views.reschedulePOD, name='reschedulePOD'),
    path('reassignPOD/<int:schedule_id>/', scheduler_views.reassignPOD, name='reassignPOD'),
    path('faculty-tally-pre-oral/', scheduler_views.faculty_tally_viewPOD, name='faculty_tallyPOD'),
    path('reset-schedulePOD/', scheduler_views.reset_schedulePOD, name='reset_schedulePOD'),
    # for exporting
    path('export/excel/pod', scheduler_views.export_schedules_excel_pod, name='export_schedules_excel_pod'),
    path('export/pdf/pod', scheduler_views.export_schedules_pdf_pod, name='export_schedules_pdf_pod'),

    path('group/list/', scheduler_views.group_infoPOD, name='group_listPOD'),
    path('group/update/<int:group_id>/', scheduler_views.update_groupPOD, name='update_groupPOD'),
    path('group/delete/<int:id>/', scheduler_views.delete_groupPOD, name='delete_groupPOD'),
    path('grade_view/<int:title_id>/', scheduler_views.grade_view, name='grade_view'),
    path('group_grades/<int:group_id>/', scheduler_views.group_grades, name='group_grades'),  

    # Mock defense schedule related URL patterns
    path('checker3/', scheduler_views.checker3, name='checker3'),
    path('mgroup/update/<int:mgroup_id>/', scheduler_views.update_groupMD, name='update_groupMD'),
    path('mgroup/delete/<int:id>/', scheduler_views.delete_groupMD, name='delete_groupMD'),
    path('schedule_listMD/', scheduler_views.schedule_listMD, name='schedule_listMD'), 
    path('rescheduleMD/<int:scheduleMD_id>/', scheduler_views.rescheduleMD, name='rescheduleMD'),
    path('reassignMD/<int:schedule_id>/', scheduler_views.reassignMD, name='reassignMD'),
    path('faculty-tally-mock/', scheduler_views.faculty_tally_viewMD, name='faculty_tallyMD'),
    path('reset-scheduleMD/', scheduler_views.reset_scheduleMD, name='reset_scheduleMD'),

    # for exporting
    path('export/excel/md', scheduler_views.export_schedules_excel_md, name='export_schedules_excel_md'),
    path('export/pdf/md', scheduler_views.export_schedules_pdf_md, name='export_schedules_pdf_md'),

    # Final defense schedule related URL patterns
    path('checker4/', scheduler_views.checker4, name='checker4'),
    path('fgroup/update/<int:fgroup_id>/', scheduler_views.update_groupFD, name='update_groupFD'),
    path('fgroup/delete/<int:id>/', scheduler_views.delete_groupFD, name='delete_groupFD'),
    path('schedule_listFD/', scheduler_views.schedule_listFD, name='schedule_listFD'), 
    path('rescheduleFD/<int:scheduleFD_id>/', scheduler_views.rescheduleFD, name='rescheduleFD'),
    path('reassignFD/<int:schedule_id>/', scheduler_views.reassignFD, name='reassignFD'),
    path('faculty-tally-final/', scheduler_views.faculty_tally_viewFD, name='faculty_tallyFD'),
    path('reset-scheduleFD/', scheduler_views.reset_scheduleFD, name='reset_scheduleFD'),

    # for exporting
    path('export/excel/fd', scheduler_views.export_schedules_excel_fd, name='export_schedules_excel_fd'),
    path('export/pdf/fd', scheduler_views.export_schedules_pdf_fd, name='export_schedules_pdf_fd'),

    # Faculty related URL patterns
    # path('input_grade/<int:schedule_id>/', input_grade, name='input_grade'),
    # path('evaluate/', evaluate_capstone, name='evaluate_capstone'),
    # path('adviser/record/<int:adviser_id>/', adviser_record_detail, name='adviser_record_detail'),
    # path('update_grade/<int:schedule_id>/', update_grade, name='update_grade'),
    # path('update_capstone/<int:grade_id>/', update_capstone, name='update_capstone'),
    path('carousel/', scheduler_views.carousel_view, name='carousel_page'),

    # adviser_list modal
    path('get_faculty/', reco_views.get_faculty, name='get_faculty'),
    path('get_group_members/', reco_views.get_group_members, name='get_group_members'),


    # PreOral Evaluation related urls
    path('input_grade/<int:schedule_id>/', input_grade, name='input_grade'),
    path('evaluate<int:schedule_id>', evaluate_capstone, name='evaluate_capstone'),
    path('update_evaluate_capstone/<int:schedule_id>/', update_evaluate_capstone, name='update_evaluate_capstone'),
    path('adviser/record/<int:adviser_id>/', adviser_record_detail, name='adviser_record_detail'),
    path('reco/<int:schedule_id>/', reco, name='reco'),

    path('add-section/', add_section, name='add_section'),
    path('edit-section/<int:section_id>/', edit_section, name='edit_section'),
    path('delete-section/<int:section_id>/', delete_section, name='delete_section'),
    path('get_section_details/<int:section_id>/', get_section_details, name='get_section_details'),

    path('add-criteria/<int:section_id>/', add_criteria, name='add_criteria'),
    path('edit-criteria/<int:criterion_id>/', edit_criteria, name='edit_criteria'),
    path('delete-criteria/<int:criterion_id>/', delete_criteria, name='delete_criteria'),

    path('add-criteria-description/<int:criterion_id>/', add_criteria_description, name='add_criteria_description'),
    path('edit-criteria-description/<int:description_id>/', edit_criteria_description, name='edit_criteria_description'),
    path('delete-criteria-description/<int:description_id>/', delete_criteria_description, name='delete_criteria_description'),

    path('add-verdict/', add_verdict, name='add_verdict'),
    path('edit-verdict/<int:verdict_id>/', edit_verdict, name='edit_verdict'),
    path('delete-verdict/<int:verdict_id>/', delete_verdict, name='delete_verdict'),

    path('view-sections/', view_section, name='view_section'),
    path('view-criteria/<int:criterion_id>/', view_criteria, name='view_criteria'),

    # path('get_verdict_checkboxes/', get_verdict_checkboxes, name='get_verdict_checkboxes'),



    # Mock defense relaated urls
    path('mock-add-section/', mock_add_section, name='mock_add_section'),
    path('mock-edit-section/<int:section_id>/', mock_edit_section, name='mock_edit_section'),
    path('mock-delete-section/<int:section_id>/', mock_delete_section, name='mock_delete_section'),
    path('mock_get_section_details/<int:section_id>/', mock_get_section_details, name='mock_get_section_details'),

    path('mock-add-criteria/<int:section_id>/', mock_add_criteria, name='mock_add_criteria'),
    path('mock-edit-criteria/<int:criterion_id>/', mock_edit_criteria, name='mock_edit_criteria'),
    path('mock-delete-criteria/<int:criterion_id>/', mock_delete_criteria, name='mock_delete_criteria'),

    path('mock-view-sections/', mock_view_section, name='mock_view_section'),
    path('mock-view-criteria/<int:criterion_id>/', mock_view_criteria, name='mock_view_criteria'),

    path('mock_add-criteria-description/<int:criterion_id>/', mock_add_criteria_description, name='mock_add_criteria_description'),
    path('mock_edit-criteria-description/<int:description_id>/', mock_edit_criteria_description, name='mock_edit_criteria_description'),
    path('mock_delete-criteria-description/<int:description_id>/', mock_delete_criteria_description, name='mock_delete_criteria_description'),

    path('mock-add-verdict/', mock_add_verdict, name='mock_add_verdict'),
    path('mock-edit-verdict/<int:verdict_id>/', mock_edit_verdict, name='mock_edit_verdict'),
    path('mock-delete-verdict/<int:verdict_id>/', mock_delete_verdict, name='mock_delete_verdict'),

    path('mock-input_grade/<int:schedule_id>/', mock_input_grade, name='mock_input_grade'),
    path('mock-evaluate<int:schedule_id>', mock_evaluate_capstone, name='mock_evaluate_capstone'),
    path('mock-update_evaluate_capstone/<int:schedule_id>/', mock_update_evaluate_capstone, name='mock_update_evaluate_capstone'),
    path('adviser/mock-record/<int:adviser_id>/', mock_adviser_record_detail, name='mock_adviser_record_detail'),
    path('mock_reco/<int:schedule_id>/', mock_reco, name='mock_reco'),
    path('mock-group_grade/<int:title_id>/', scheduler_views.mock_grade_view, name='mock_grade_view'),
    path('groupsMD/', scheduler_views.group_infoMD, name='group_infoMD'),



    # Final defense related urls
    path('final-add-section/', final_add_section, name='final_add_section'),
    path('final-edit-section/<int:section_id>/', final_edit_section, name='final_edit_section'),
    path('final-delete-section/<int:section_id>/', final_delete_section, name='final_delete_section'),
    path('final_get_section_details/<int:section_id>/', final_get_section_details, name='final_get_section_details'),

    path('final-add-criteria/<int:section_id>/', final_add_criteria, name='final_add_criteria'),
    path('final-edit-criteria/<int:criterion_id>/', final_edit_criteria, name='final_edit_criteria'),
    path('final-delete-criteria/<int:criterion_id>/', final_delete_criteria, name='final_delete_criteria'),

    path('final-view-sections/', final_view_section, name='final_view_section'),

    path('final_add-criteria-description/<int:criterion_id>/', final_add_criteria_description, name='final_add_criteria_description'),
    path('final_edit-criteria-description/<int:description_id>/', final_edit_criteria_description, name='final_edit_criteria_description'),
    path('final_delete-criteria-description/<int:description_id>/', final_delete_criteria_description, name='final_delete_criteria_description'),

    path('final-add-verdict/', final_add_verdict, name='final_add_verdict'),
    path('final-edit-verdict/<int:verdict_id>/', final_edit_verdict, name='final_edit_verdict'),
    path('final-delete-verdict/<int:verdict_id>/', final_delete_verdict, name='final_delete_verdict'),

    path('final-input_grade/<int:schedule_id>/', final_input_grade, name='final_input_grade'),
    path('final-evaluate<int:schedule_id>', final_evaluate_capstone, name='final_evaluate_capstone'),
    path('final-update_evaluate_capstone/<int:schedule_id>/', final_update_evaluate_capstone, name='final_update_evaluate_capstone'),
    path('adviser/final-record/<int:adviser_id>/', final_adviser_record_detail, name='final_adviser_record_detail'),
    path('final_reco/<int:schedule_id>/', final_reco, name='final_reco'),
    path('final-group_grade/<int:title_id>/', scheduler_views.final_grade_view, name='final_grade_view'),
    path('groupsFD/', scheduler_views.group_infoFD, name='group_infoFD'),



    # cloning evaluation form related urls
    path('pre_oral_clone_records/', pre_oral_clone_records, name='pre_oral_clone_records'),
    path('mock_clone_records/', mock_clone_records, name='mock_clone_records'),
    path('final_clone_records/', final_clone_records, name='final_clone_records'),


    # viewing evaluation form related urls
    path('view_input_grade/', view_input_grade, name='view_input_grade'),
    path('view_mock_input_grade/', view_mock_input_grade, name='view_mock_input_grade'),
    path('view_final_input_grade/', view_final_input_grade, name='view_final_input_grade'),

    # View all schedules
    # path('view_all_schedules/', view_all_schedules, name='view_all_schedules'),

    path('create-new-account/', create_new_account, name='create_new_account'),


    # for accepting or declining the advisee
    path('adviser/<int:adviser_id>/accept/', accept_adviser, name='accept_adviser'),
    path('adviser/<int:adviser_id>/decline/', decline_adviser, name='decline_adviser'),

    # for the notifications
    path('notifications/', notification_list, name='notifications'),
    path('notifications/mark-as-read/<int:notif_id>/', mark_notification_as_read, name='mark_notification_as_read'),
    path('notifications/mark_all_notifications_as_read/', mark_all_notifications_as_read, name='mark_all_notifications_as_read'),

    path('accept-adviser/<int:adviser_id>/mark-read/<int:notif_id>/', accept_adviser_and_mark_read, name='accept_adviser_and_mark_read'),
    path('decline-adviser/<int:adviser_id>/mark-read/<int:notif_id>/', decline_adviser_and_mark_read, name='decline_adviser_and_mark_read'),

    
]
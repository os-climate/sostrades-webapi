import time

from flask import make_response, jsonify, Response
from werkzeug.exceptions import abort

from sos_trades_api.base_server import app
from sos_trades_api.controllers.sostrades_data.calculation_controller import calculation_status, execute_calculation
from sos_trades_api.controllers.sostrades_main.study_case_controller import load_study_case, light_load_study_case, \
    create_study_case, update_study_parameters
from sos_trades_api.controllers.sostrades_post_processing.post_processing_controller import \
    load_post_processing_graph_filters, load_post_processing
from sos_trades_api.models.database_models import StudyCaseExecution, StudyCase, User, StudyCaseChange
from sos_trades_api.tools.authentication.authentication import auth_required, get_authenticated_user
from sos_trades_api.tools.right_management.functional.study_case_access_right import StudyCaseAccess
from sos_trades_core.tools.post_processing.post_processing_bundle import PostProcessingBundle
from sos_trades_core.tools.post_processing.post_processing_factory import PostProcessingFactory
from sos_trades_saas.tools.credentials import restricted_viewer_required


@app.route(f'/saas/load/postprocess/<int:study_id>', methods=['GET'])
@auth_required
@restricted_viewer_required
def load_post_process(study_id: int):
    try:

        user = get_authenticated_user()
        study_case_access = StudyCaseAccess(user.id)
        study_access_right = study_case_access.get_user_right_for_study(study_id)

        study_manager = light_load_study_case(study_id)
        post_processing_factory = PostProcessingFactory()

        all_post_processings_bundle = post_processing_factory.get_all_post_processings(
            study_manager.execution_engine,
            filters_only=True)
        print(all_post_processings_bundle)
        all_post_processings_bundle = post_processing_factory.get_all_post_processings(
            study_manager.execution_engine,
            filters_only=False)
        print(all_post_processings_bundle)

        return make_response(jsonify(all_post_processings_bundle), 200)

    except Exception as e:
        abort(400, str(e))


@app.route(f'/saas/update/parameter', methods=['POST', "GET"])
# @auth_required
def update_study_case_test():

    # See update_study_parameters controller
    # See test_update_study_parameters test
    # See update_study_parameters_by_study_case_id route

    study_id = 10
    user = User.query.filter(
        User.id == 2).first()
    study_test = StudyCase.query.filter(
        StudyCase.id == study_id).first()
    parameters_to_save = [
        {"variableId": f'{study_test.name}.sub_mda_class',
         # "variableType": "float",
         "changeType": StudyCaseChange.SCALAR_CHANGE,
         "newValue": "MDAGaussSeidel",
         "oldValue": "toto",
         'namespace': f'{study_test.name}',
         'discipline': 'sub_mda_class',
         "lastModified": "2021-01-11T13:51:26.118Z", "id": None, "author": None}
    ]
    # parameters_to_save = [
    #     {"variableId": f'{study_test.name}.sub_mda_class',
    #      # "variableType": "float",
    #      "changeType": StudyCaseChange.SCALAR_CHANGE,
    #      "newValue": "MDAGaussSeidel",
    #      "oldValue": "toto",
    #      'namespace': f'{study_test.name}',
    #      'discipline': 'sub_mda_class',
    #      "lastModified": "2021-01-11T13:51:26.118Z", "id": None, "author": None}
    # ]
    update_study_parameters(study_id, user, None, None, parameters_to_save)
    return Response({"hello": "hello you"}, status=200)



""""""""""""""""""""

# Tools route

""""""""""""""""""""

@app.route(f'/saas/create_study/', methods=['GET'])
def add_study_to_db():
    # Care to this
    # It really add a study to db
    loaded_study = create_study_case(
        2,
        "test_rat",
        "value_assessment.sos_processes",
        # "sos_trades_core.sos_processes.test",
        # "test_architecture",
        "generic_value_assessment",
        1,
        "Reference")

    return make_response(jsonify({"study created ": str(loaded_study)}), status=200)



@app.route(f'/saas/trigger/postprocess/<int:study_id>', methods=['GET'])
def postprocess(study_id):
    study_manager = light_load_study_case(study_id)
    execute_calculation(study_id, "user_test")
    return Response({"hello": "hello you"}, status=200)

